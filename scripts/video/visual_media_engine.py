"""
Visual Media Engine — busca e geração de mídia por cena (footage-first).

Cadeia de fallback por cena (youtube_dark):
  1. Stock ranqueado — Media Search Orchestrator (Wikimedia → Pixabay → Pexels)
  2. Foto stock + Ken Burns / fallback editorial (mapa, timeline, gráfico)
  3. T2V seletivo — máx. 2 cenas/vídeo (n8n ou VideoGenerator local: Kling → fal → Replicate → HF).
     Cenas preferir_imagem pulam T2V e usam imagem + Ken Burns (~$0,03/imagem vs ~$0,25/clip T2V).
  4. Imagem IA documental — Replicate Flux → Pollinations → HF (bloqueado em cenas críticas)
  5. Placeholder ilustrativo — se tudo falhar

Todos os assets passam pelo Asset Rights Ledger antes do render.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import requests

from scripts.video.pexels_provider import search_pexels
from scripts.video.pixabay_provider import search_pixabay
from scripts.video.wikimedia_provider import search_wikimedia
from scripts.video.media_providers.pollinations_provider import (
    generate_pollinations_image,
    generate_pollinations_video,
)
from src.prompt_builder import get_best_movement, build_scene_video_prompt, build_scene_image_prompt
from src.video_generator import (
    VideoGenerator,
    fal_kling_is_configured,
    falai_is_configured,
    replicate_is_configured,
    kling_web_is_configured,
)
from src.video_upscaler import upscale_video_ffmpeg
from scripts.video.media_providers.huggingface.adapter import (
    generate_hf_image,
    hf_is_configured,
)
from scripts.video.asset_ranking import pick_ranked_assets, selection_signature
from scripts.video.relevance_feedback import RejectionLog
from scripts.video.media_providers.relevance import (
    MIN_ACCEPTABLE_QUALITY_SCORE,
    MIN_PHOTO_RELEVANCE_SCORE,
    MIN_RELEVANCE_SCORE,
    best_video_score,
    score_photo,
    score_video,
)
from scripts.core.visual_intent_engine import resolve_visual_intent
from scripts.video.query_localizer import (
    is_critical_scene,
    localize_search_query,
    should_prioritize_wikimedia,
    wikimedia_query_variants,
)
from src.n8n_integration.scene_integration import (
    generate_scene_video_fallback,
    use_n8n_for_scenes,
)
from scripts.video.media_downloader import (
    download_file,
    select_photo_url,
    select_video_file_with_fallback,
)
from scripts.video.media_quality import (
    MIN_IMAGE_HEIGHT,
    MIN_IMAGE_HEIGHT_FALLBACK,
    MIN_IMAGE_WIDTH,
    MIN_IMAGE_WIDTH_FALLBACK,
    MIN_VIDEO_HEIGHT,
    MIN_VIDEO_HEIGHT_FALLBACK,
    MIN_VIDEO_WIDTH,
    MIN_VIDEO_WIDTH_FALLBACK,
    validate_image_file,
    validate_video_file,
)
from scripts.core.asset_rights_ledger import AssetRightsLedger, evaluate_license
from scripts.video.media_search_orchestrator import search_and_rank_scene
from scripts.scoring.visual_relevance_scorer import (
    FALLBACK_KEEP,
    TOP_CANDIDATES,
    rank_candidates_with_visual_score,
)
from scripts.core.feature_flags import sprint30_visual_score
from scripts.video.editorial_fallback import execute_editorial_fallback
from scripts.video.t2v_decision import T2VDecision, T2VTracker, evaluate_t2v_decision

REPLICATE_PREDICTIONS_URL = "https://api.replicate.com/v1/predictions"
REPLICATE_FLUX_MODEL = os.getenv("REPLICATE_FLUX_MODEL", "black-forest-labs/flux-schnell")
MAX_T2V_SCENES_PER_VIDEO = int(os.getenv("MAX_T2V_SCENES_PER_VIDEO", "2"))
REPLICATE_FLUX_POLL_INTERVAL = float(os.getenv("REPLICATE_FLUX_POLL_INTERVAL", "2"))
REPLICATE_FLUX_TIMEOUT = float(os.getenv("REPLICATE_FLUX_TIMEOUT", "120"))

_t2v_scenes_used = 0


def _reset_t2v_budget() -> None:
    """Reinicia contador de cenas T2V pagas por execução de pipeline."""

    global _t2v_scenes_used
    _t2v_scenes_used = 0


def _t2v_budget_available() -> bool:
    """True enquanto houver slots T2V disponíveis neste vídeo."""

    return _t2v_scenes_used < MAX_T2V_SCENES_PER_VIDEO


def _consume_t2v_budget() -> None:
    """Registra consumo de um slot T2V."""

    global _t2v_scenes_used
    _t2v_scenes_used += 1


def _output_folder(subject):
    from scripts.utils.slug import content_output_dir

    platform = subject.get("_output_platform")
    return content_output_dir(subject, platform=platform)


def _has_media(media: dict) -> bool:
    return bool(media.get("videos") or media.get("photos"))


_CINEMATIC_SUFFIX = {
    "hook": "dramatic cinematic establishing shot",
    "contexto": "historical documentary aerial",
    "desenvolvimento_1": "documentary investigation footage",
    "desenvolvimento_2": "historical event dramatic b-roll",
    "revelacao": "dramatic reveal documentary",
    "consequencias": "impact consequences documentary",
    "impacto": "legacy modern impact documentary",
    "encerramento": "cinematic closing atmospheric",
}

MAX_SEARCH_QUERY_LEN = 72


def _truncate_query(query: str, max_len: int = MAX_SEARCH_QUERY_LEN) -> str:
    cleaned = " ".join(query.split()).strip()
    if len(cleaned) <= max_len:
        return cleaned

    words = cleaned.split()
    result = []
    length = 0
    for word in words:
        next_len = length + len(word) + (1 if result else 0)
        if next_len > max_len:
            break
        result.append(word)
        length = next_len

    return " ".join(result).strip() or cleaned[:max_len].strip()


def _upscale_image(path: Path, width: int = 1920, height: int = 1080) -> bool:
    temp_path = path.with_suffix(".upscaled.jpg")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(path.resolve()),
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
        "-q:v", "2",
        str(temp_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        if temp_path.exists():
            temp_path.replace(path)
            return True
    except subprocess.CalledProcessError:
        if temp_path.exists():
            temp_path.unlink()
    return False


def _enrich_search_query(
    busca: str,
    tipo: str,
    fallback: str = "",
    tematica: str = "",
    atmosfera: str = "",
) -> list[str]:
    """
    Monta queries em 3 níveis + fallback legado (sem duplicatas).
    1. Específica (busca)  2. Temática  3. Atmosfera/emotion  4. Fallback
    """

    queries: list[str] = []

    for candidate in (busca, tematica, atmosfera, fallback):
        cleaned = _truncate_query(localize_search_query((candidate or "").strip()))
        if cleaned and cleaned not in queries:
            queries.append(cleaned)

    suffix = _CINEMATIC_SUFFIX.get(tipo, "documentary cinematic")
    if busca.strip():
        enriched = _truncate_query(
            localize_search_query(f"{busca.strip()} {suffix}", append_documentary=False)
        )
        if enriched and enriched not in queries:
            queries.append(enriched)

    return [q for q in queries if q]


def _merge_media(target: dict, source: dict) -> None:
    seen_videos = {video.get("id") for video in target.get("videos", []) if video.get("id")}
    seen_photos = {photo.get("id") for photo in target.get("photos", []) if photo.get("id")}

    for video in source.get("videos", []):
        vid = video.get("id")
        if vid and vid in seen_videos:
            continue
        if vid:
            seen_videos.add(vid)
        target.setdefault("videos", []).append(video)

    for photo in source.get("photos", []):
        pid = photo.get("id")
        if pid and pid in seen_photos:
            continue
        if pid:
            seen_photos.add(pid)
        target.setdefault("photos", []).append(photo)


def _search_providers_chain(
    query: str,
    *,
    photos_only: bool = False,
    skip_wikimedia: bool = False,
) -> tuple[dict, str]:
    """Busca Wikimedia → Pixabay → Pexels até encontrar mídia."""

    query = _truncate_query(localize_search_query(query))

    providers: tuple[tuple[str, Any], ...] = (
        ("wikimedia", search_wikimedia),
        ("pixabay", search_pixabay),
        ("pexels", search_pexels),
    )
    if skip_wikimedia:
        providers = providers[1:]

    for provider_name, search_fn in providers:
        media = search_fn(query)
        if photos_only:
            media = {"videos": [], "photos": media.get("photos", [])}
        if _has_media(media):
            return media, provider_name
        if provider_name == "pexels":
            print(f"[Pexels] Nenhum resultado para: {query}")

    return {"videos": [], "photos": []}, "none"


def _search_wikimedia_priority(
    query: str,
    query_item: dict | None,
    *,
    photos_only: bool = False,
) -> tuple[dict, str]:
    """Passa extra no Wikimedia com variações antes de stock genérico."""
    for variant in wikimedia_query_variants(query, query_item):
        media = search_wikimedia(variant)
        if photos_only:
            media = {"videos": [], "photos": media.get("photos", [])}
        if media.get("photos"):
            return media, "wikimedia"
    return {"videos": [], "photos": []}, "none"


def _search_all_providers(
    query: str,
    *,
    photos_only: bool = False,
    query_item: dict | None = None,
) -> tuple[dict, str]:
    """Cadeia ordenada de provedores com prioridade Wikimedia em cenas históricas."""

    if should_prioritize_wikimedia(query_item):
        media, source = _search_wikimedia_priority(
            query,
            query_item,
            photos_only=photos_only,
        )
        if _has_media(media):
            return media, source

    return _search_providers_chain(
        query,
        photos_only=photos_only,
        skip_wikimedia=should_prioritize_wikimedia(query_item),
    )


def _download_scene_video(video: dict, path: Path) -> bool:
    url, min_w, min_h = select_video_file_with_fallback(video)
    if not url:
        return False

    try:
        if path.exists():
            path.unlink()

        download_file(url, path)

        for attempt_min_w, attempt_min_h in (
            (min_w, min_h),
            (MIN_VIDEO_WIDTH_FALLBACK, MIN_VIDEO_HEIGHT_FALLBACK),
        ):
            valid, reason = validate_video_file(
                path,
                min_width=attempt_min_w,
                min_height=attempt_min_h,
            )
            if valid:
                return True

        print(f"  ⚠️ Vídeo rejeitado ({reason}): {path.name}")
        if path.exists():
            path.unlink()
        return False

    except Exception as error:
        print(f"Erro baixando vídeo da cena: {error}")
        if path.exists():
            path.unlink()
        return False


def _download_scene_photo(photo: dict, path: Path) -> bool:
    url = select_photo_url(photo, min_width=MIN_IMAGE_WIDTH)
    if not url:
        return False

    try:
        if path.exists():
            path.unlink()

        download_file(url, path)

        for attempt_min_w, attempt_min_h in (
            (MIN_IMAGE_WIDTH, MIN_IMAGE_HEIGHT),
            (MIN_IMAGE_WIDTH_FALLBACK, MIN_IMAGE_HEIGHT_FALLBACK),
        ):
            valid, reason = validate_image_file(
                path,
                min_width=attempt_min_w,
                min_height=attempt_min_h,
            )
            if valid:
                return True

        print(f"  ⚠️ Imagem rejeitada ({reason}): {path.name}")
        if path.exists():
            path.unlink()
        return False

    except Exception as error:
        print(f"Erro baixando imagem da cena: {error}")
        if path.exists():
            path.unlink()
        return False


def _story_params(query_item: dict | None) -> tuple[Any, str, str, str, str, list]:
    """Extrai sinais story-aware da query (neutros entre providers)."""

    if not query_item:
        return None, "calm", "", "", "", []

    visual_intent = resolve_visual_intent({
        "visual_intent": query_item.get("visual_intent", "general_narrative"),
        "emotion": query_item.get("emotion", "calm"),
        "camera_motion": query_item.get("camera_motion", "slow_push"),
    })
    emotion = query_item.get("emotion", "calm")
    narrative_moment = query_item.get("tipo", "")
    style = query_item.get("style", "")
    camera = query_item.get("camera", "")
    avoid = query_item.get("avoid") or []
    return visual_intent, emotion, narrative_moment, style, camera, avoid


def _try_stock_videos(
    query: str,
    media: dict,
    scene_video: Path,
    used_ids: set,
    query_item: dict | None = None,
    provider: str = "",
    recent_selections: list | None = None,
    rejections: RejectionLog | None = None,
    scene_num: int = 0,
) -> tuple[bool, dict | None, float]:
    """Tenta baixar vídeos stock ranqueados por Asset Quality Score."""

    visual_intent, emotion, narrative_moment, style, camera, avoid = _story_params(query_item)

    candidates = pick_ranked_assets(
        query,
        media.get("videos", []),
        media_type="video",
        visual_intent=visual_intent,
        emotion=emotion,
        provider=provider,
        used_ids=used_ids,
        limit=8,
        narrative_moment=narrative_moment,
        style=style,
        camera=camera,
        avoid=avoid,
        recent_selections=recent_selections,
    )

    for video in candidates:
        quality_score = score_video(query, video)
        if quality_score < MIN_ACCEPTABLE_QUALITY_SCORE:
            if rejections:
                rejections.record(
                    scene=scene_num, item=video, score=quality_score,
                    rejected_reason="weak_storytelling", provider=provider, query=query,
                )
            continue

        if _download_scene_video(video, scene_video):
            return True, video, round(quality_score, 3)

    return False, None, 0.0


def _try_stock_photos(
    query: str,
    media: dict,
    scene_image: Path,
    used_ids: set,
    query_item: dict | None = None,
    provider: str = "",
    recent_selections: list | None = None,
    rejections: RejectionLog | None = None,
    scene_num: int = 0,
) -> tuple[bool, dict | None]:
    """Tenta baixar fotos stock ranqueadas por Asset Quality Score."""

    visual_intent, emotion, narrative_moment, style, camera, avoid = _story_params(query_item)

    candidates = pick_ranked_assets(
        query,
        media.get("photos", []),
        media_type="photo",
        visual_intent=visual_intent,
        emotion=emotion,
        provider=provider,
        used_ids=used_ids,
        limit=5,
        narrative_moment=narrative_moment,
        style=style,
        camera=camera,
        avoid=avoid,
        recent_selections=recent_selections,
    )

    for photo in candidates:
        photo_score = score_photo(query, photo)
        if photo_score < MIN_PHOTO_RELEVANCE_SCORE:
            if rejections:
                rejections.record(
                    scene=scene_num, item=photo, score=photo_score,
                    rejected_reason="weak_storytelling", provider=provider, query=query,
                )
            continue
        if _download_scene_photo(photo, scene_image):
            return True, photo

    return False, None


def _try_hf_image(prompt: str, scene_image: Path) -> bool:
    """Tenta HF Inference Providers; retorna False se não configurada ou falhar."""

    if not hf_is_configured():
        return False
    try:
        return generate_hf_image(prompt, scene_image)
    except Exception:
        return False


def _try_replicate_flux_image(prompt: str, scene_image: Path) -> bool:
    """
    Gera imagem via Replicate Flux Schnell (~$0,003/img).

    Modelo recomendado em templates n8n dark (Black Forest Labs / flux-schnell).
    """
    token = os.getenv("REPLICATE_API_TOKEN", "")
    if not token:
        return False

    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json",
    }
    create_url = f"https://api.replicate.com/v1/models/{REPLICATE_FLUX_MODEL}/predictions"
    payload = {
        "input": {
            "prompt": prompt,
            "aspect_ratio": "16:9",
            "output_format": "jpg",
            "output_quality": 80,
            "go_fast": True,
            "num_outputs": 1,
        }
    }

    try:
        response = requests.post(create_url, headers=headers, json=payload, timeout=60)
        if response.status_code >= 400:
            return False

        prediction_id = response.json().get("id")
        if not prediction_id:
            return False

        status_url = f"{REPLICATE_PREDICTIONS_URL}/{prediction_id}"
        deadline = time.time() + REPLICATE_FLUX_TIMEOUT

        while time.time() < deadline:
            poll = requests.get(status_url, headers=headers, timeout=30)
            if poll.status_code >= 400:
                return False

            body = poll.json()
            status = body.get("status", "")
            if status == "succeeded":
                output = body.get("output")
                image_url = output[0] if isinstance(output, list) and output else output
                if isinstance(image_url, str) and image_url.startswith("http"):
                    return download_file(image_url, scene_image)
                return False

            if status in ("failed", "canceled"):
                return False

            time.sleep(REPLICATE_FLUX_POLL_INTERVAL)

        return False
    except (requests.RequestException, OSError, TypeError, ValueError):
        return False


def _try_ai_image(
    prompt: str,
    scene_image: Path,
    suffix: str = "",
    *,
    allow_upscale: bool = True,
    allow_pollinations: bool = True,
    scene_description: str = "",
    scene_tipo: str = "",
    emotion: str = "",
    platform: str = "youtube_dark",
    visual_direction: dict | None = None,
) -> tuple[bool, str]:
    bundle = build_scene_image_prompt(
        scene_description=scene_description or prompt,
        scene_query=localize_search_query(prompt),
        platform=platform,
        scene_tipo=scene_tipo,
        emotion=emotion,
        visual_direction=visual_direction,
        retry_suffix=suffix,
        max_length=280,
    )
    ai_prompt = bundle["prompt"]
    provider = ""
    generated = False
    if allow_pollinations:
        generated = generate_pollinations_image(ai_prompt, scene_image)
        if generated:
            provider = "pollinations"
    if not generated and _try_replicate_flux_image(ai_prompt, scene_image):
        generated = True
        provider = "replicate_flux"
    if not generated and _try_hf_image(ai_prompt, scene_image):
        generated = True
        provider = "huggingface"
    if not generated:
        return False, ""

    thresholds = [
        (MIN_IMAGE_WIDTH, MIN_IMAGE_HEIGHT),
        (MIN_IMAGE_WIDTH_FALLBACK, MIN_IMAGE_HEIGHT_FALLBACK),
        (1024, 576),
    ]

    for min_w, min_h in thresholds:
        valid, reason = validate_image_file(
            scene_image,
            min_width=min_w,
            min_height=min_h,
        )
        if valid:
            if allow_upscale and (min_w < MIN_IMAGE_WIDTH or min_h < MIN_IMAGE_HEIGHT):
                _upscale_image(scene_image)
            return True, provider
        print(f"  ⚠️ Imagem IA rejeitada ({reason})")

    if allow_upscale and _upscale_image(scene_image):
        valid, _ = validate_image_file(
            scene_image,
            min_width=MIN_IMAGE_WIDTH_FALLBACK,
            min_height=MIN_IMAGE_HEIGHT_FALLBACK,
        )
        if valid:
            return True, provider

    if scene_image.exists():
        scene_image.unlink()
    return False, ""


def _try_local_reuse(
    scene_video: Path,
    scene_image: Path,
    saved_assets: list[Path],
    *,
    prefer_image: bool,
) -> bool:
    """Reutiliza asset local já baixado em cena anterior."""

    for source in reversed(saved_assets):
        if not source.exists():
            continue

        target = scene_image if source.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} else scene_video
        if prefer_image and target.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            target = scene_image

        try:
            shutil.copy2(source, target)
            return target.exists()
        except OSError:
            continue

    return False


def _generate_placeholder_image(
    prompt: str,
    scene_image: Path,
    scene_num: int,
    *,
    allow_pollinations: bool = True,
) -> bool:
    """Gera imagem ilustrativa mínima quando todos os provedores falham."""

    label = _truncate_query(localize_search_query(prompt or f"scene {scene_num}"), max_len=40)
    safe_label = label.replace(":", "\\:").replace("'", "\\'")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x1a1a2e:s=1920x1080:d=1",
        "-vf",
        (
            f"drawtext=text='{safe_label}':fontcolor=white:fontsize=42:"
            "x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.45"
        ),
        "-frames:v", "1",
        str(scene_image),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return scene_image.exists()
    except subprocess.CalledProcessError:
        if not allow_pollinations:
            return False
        saved, _ = _try_ai_image(
            prompt,
            scene_image,
            ", atmospheric documentary illustration",
            allow_upscale=True,
            allow_pollinations=True,
            scene_description=prompt,
            platform="youtube_dark",
        )
        return saved


def _ai_video_configured() -> bool:
    """True se alguma API de vídeo IA está configurada."""
    return (
        kling_web_is_configured()
        or fal_kling_is_configured()
        or replicate_is_configured()
        or falai_is_configured()
    )


def _try_ai_video(
    prompt: str,
    scene_video: Path,
    *,
    image_url: str | None = None,
    product_name: str | None = None,
    category: str | None = None,
    material: str | None = None,
    scene_description: str = "",
    scene_tipo: str = "",
    emotion: str = "",
    platform: str = "youtube_dark",
    visual_direction: dict | None = None,
    allow_pollinations: bool = True,
) -> tuple[bool, str]:
    """
    Gera vídeo IA via VideoGenerator (Kling Web → fal Kling 2.6 → Replicate Wan → HF).
    Com image_url: fluxo I2V e-commerce (fal Kling / Replicate Wan + upscale 2x).
    Sem image_url: T2V documental YouTube Dark via build_scene_video_prompt.
    Pollinations só entra como último recurso em cenas não críticas.
    """
    localized_prompt = localize_search_query(prompt)
    localized_description = localize_search_query(scene_description or prompt)

    if image_url and (fal_kling_is_configured() or replicate_is_configured()) and product_name:
        try:
            generator = VideoGenerator(output_dir=scene_video.parent)
            movement = get_best_movement(category or "")
            result = generator.generate_i2v_ecommerce(
                product_name=product_name,
                image_url=image_url,
                material=material,
                movement=movement,
                download=True,
                upscale=True,
            )
            local_path = result.get("local_path")
            if local_path and Path(local_path).exists():
                src = Path(local_path)
                if src.resolve() != scene_video.resolve():
                    shutil.copy2(src, scene_video)

                valid, reason = validate_video_file(scene_video, min_duration=2.0)
                if not valid:
                    print(f"  ⚠️ Vídeo I2V rejeitado ({reason})")
                    if scene_video.exists():
                        scene_video.unlink()
                else:
                    return True, result.get("api_used", "i2v")
        except Exception as error:
            print(f"  ⚠️ I2V e-commerce falhou: {error}")

    if not image_url and _ai_video_configured():
        if fal_kling_is_configured():
            print(f"[fal.ai Kling] tentando T2V: {localized_prompt[:72]}")
        elif replicate_is_configured():
            print(f"[Replicate Wan] tentando T2V: {localized_prompt[:72]}")
        else:
            print(f"[VideoGenerator] tentando T2V via API configurada...")

        try:
            generator = VideoGenerator(output_dir=scene_video.parent)
            result = generator.generate_youtube_scene(
                scene_description=localized_description,
                scene_query=localized_prompt,
                scene_tipo=scene_tipo,
                emotion=emotion,
                visual_direction=visual_direction,
                download=True,
            )
            local_path = result.get("local_path")
            if local_path and Path(local_path).exists():
                src = Path(local_path)
                output_path = scene_video
                output_path.parent.mkdir(parents=True, exist_ok=True)
                if src.resolve() != output_path.resolve():
                    shutil.copy2(src, output_path)

                valid, reason = validate_video_file(output_path, min_duration=2.0)
                if not valid:
                    print(f"  ⚠️ Vídeo T2V rejeitado ({reason})")
                    if output_path.exists():
                        output_path.unlink()
                else:
                    try:
                        upscaled = upscale_video_ffmpeg(str(output_path), scale=2)
                        upscaled_path = Path(upscaled)
                        if upscaled_path.exists() and upscaled_path != output_path:
                            upscaled_path.replace(output_path)
                    except Exception as error:
                        print(f"  ⚠️ Upscale de vídeo ignorado: {error}")
                    return True, result.get("api_used", "replicate")
        except Exception as error:
            print(f"  ⚠️ T2V documental falhou: {error}")

        # Fallback completo (Kling Web → fal Kling → Replicate → HF) com prompt enriquecido.
        try:
            prompt_bundle = build_scene_video_prompt(
                scene_description=localized_description,
                scene_query=localized_prompt,
                platform=platform,
                scene_tipo=scene_tipo,
                emotion=emotion,
                visual_direction=visual_direction,
            )
            generator = VideoGenerator(output_dir=scene_video.parent)
            result = generator.generate(
                prompt=prompt_bundle["prompt"],
                download=True,
            )
            local_path = result.get("local_path")
            if local_path and Path(local_path).exists():
                src = Path(local_path)
                if src.resolve() != scene_video.resolve():
                    shutil.copy2(src, scene_video)
                valid, reason = validate_video_file(scene_video, min_duration=2.0)
                if valid:
                    try:
                        upscaled = upscale_video_ffmpeg(str(scene_video), scale=2)
                        upscaled_path = Path(upscaled)
                        if upscaled_path.exists() and upscaled_path != scene_video:
                            upscaled_path.replace(scene_video)
                    except Exception as upscale_error:
                        print(f"  ⚠️ Upscale de vídeo ignorado: {upscale_error}")
                    return True, result.get("api_used", "video_generator")
                if scene_video.exists():
                    scene_video.unlink()
        except Exception as error:
            print(f"  ⚠️ Fallback T2V (Kling/fal/Replicate) falhou: {error}")

        if not allow_pollinations and replicate_is_configured():
            print("[Replicate] falhou — Pollinations bloqueado em cena crítica")

    ai_prompt = f"{localized_prompt}, documentary cinematic footage"

    if _ai_video_configured() and image_url:
        try:
            prompt_bundle = build_scene_video_prompt(
                scene_description=localized_description,
                scene_query=localized_prompt,
                platform=platform,
                scene_tipo=scene_tipo,
                emotion=emotion,
                visual_direction=visual_direction,
            )
            generator = VideoGenerator(output_dir=scene_video.parent)
            result = generator.generate(
                prompt=prompt_bundle["prompt"],
                image_url=image_url,
                product_name=product_name,
                download=True,
            )
            local_path = result.get("local_path")
            if local_path and Path(local_path).exists():
                src = Path(local_path)
                if src.resolve() != scene_video.resolve():
                    shutil.copy2(src, scene_video)

                valid, reason = validate_video_file(scene_video, min_duration=2.0)
                if not valid:
                    print(f"  ⚠️ Vídeo IA rejeitado ({reason})")
                    if scene_video.exists():
                        scene_video.unlink()
                else:
                    try:
                        upscaled = upscale_video_ffmpeg(str(scene_video), scale=2)
                        upscaled_path = Path(upscaled)
                        if upscaled_path.exists() and upscaled_path != scene_video:
                            upscaled_path.replace(scene_video)
                    except Exception as error:
                        print(f"  ⚠️ Upscale de vídeo ignorado: {error}")

                    api_used = result.get("api_used", "video_generator")
                    return True, api_used
        except Exception as error:
            print(f"  ⚠️ VideoGenerator falhou: {error}")

    if not allow_pollinations:
        print(f"  ⚠️ Pollinations bloqueado em cena crítica ({scene_tipo or 'unknown'})")
        return False, "none"

    print(f"[Pollinations] tentando vídeo (último recurso)...")
    generated = generate_pollinations_video(ai_prompt, scene_video)
    if not generated:
        return False, "none"

    valid, reason = validate_video_file(scene_video, min_duration=2.0)
    if not valid:
        print(f"  ⚠️ Vídeo IA rejeitado ({reason})")
        if scene_video.exists():
            scene_video.unlink()
        return False, "none"

    return True, "pollinations"


def _register_asset_in_ledger(
    ledger: AssetRightsLedger | None,
    *,
    scene_num: int,
    provider: str,
    item: dict,
    media_type: str,
    local_path: Path,
    quality_score: float = 0.0,
    license_text: str = "",
) -> bool:
    """Registra asset no ledger; retorna False se licença insegura."""

    if ledger is None:
        return True

    record = ledger.register_asset(
        source=provider,
        provider=provider,
        source_url=item.get("page_url") or item.get("url", ""),
        download_url=item.get("url") or item.get("src", {}).get("original", ""),
        creator=item.get("credit") or item.get("photographer") or "",
        license_text=license_text or item.get("license") or item.get("credit") or "",
        media_type=media_type,
        width=item.get("width", 0),
        height=item.get("height", 0),
        topic_relevance_score=quality_score,
        visual_quality_score=quality_score,
        scene_id=scene_num,
        local_path=local_path,
        item_id=item.get("id"),
    )
    return record.is_safe


def _try_orchestrated_stock(
    scene_num: int,
    query_item: dict,
    scene: dict,
    scene_video: Path,
    scene_image: Path,
    used_ids: set,
    *,
    topic: str = "",
    prefer_image: bool = False,
    recent_selections: list | None = None,
    rejections: RejectionLog | None = None,
    ledger: AssetRightsLedger | None = None,
) -> dict | None:
    """Busca via Media Search Orchestrator e seleciona melhor asset seguro."""

    candidates = search_and_rank_scene(
        query_item,
        scene=scene,
        topic=topic,
        used_ids=used_ids,
        recent_selections=recent_selections,
        prefer_image=prefer_image,
        min_candidates=3,
    )

    if not candidates:
        print(f"  ⚠️ Cena {scene_num}: orchestrator retornou 0 candidatos")
        return None

    use_visual_score = sprint30_visual_score()

    scored_candidates = rank_candidates_with_visual_score(
        candidates,
        scene,
        topic=topic,
        limit=TOP_CANDIDATES,
    ) if use_visual_score else candidates[:TOP_CANDIDATES]

    fallbacks = []
    if use_visual_score and scored_candidates:
        fallbacks = [
            {
                "asset_id": c.get("visual_breakdown", {}).get("asset_id"),
                "visual_score": c.get("visual_score"),
                "provider": c.get("provider"),
                "rank": index + 1,
            }
            for index, c in enumerate(scored_candidates[1:FALLBACK_KEEP + 1])
        ]

    top_score = (
        scored_candidates[0].get("visual_score", 0)
        if use_visual_score and scored_candidates
        else 0
    )
    print(
        f"  📋 Cena {scene_num}: {len(candidates)} candidatos"
        + (f", top visual {top_score:.0f}/100" if use_visual_score else "")
    )

    for rank, candidate in enumerate(scored_candidates[:5], 1):
        item = candidate["item"]
        provider = candidate["provider"]
        media_type = candidate["media_type"]
        score = candidate["score"]
        query = candidate["query"]

        license_eval = evaluate_license(
            candidate.get("license_text", ""),
            provider=provider,
        )
        if not license_eval["is_safe"]:
            if rejections:
                rejections.record(
                    scene=scene_num, item=item, score=score,
                    rejected_reason="unsafe_license", provider=provider, query=query,
                )
            continue

        if media_type == "video":
            if _download_scene_video(item, scene_video):
                if not _register_asset_in_ledger(
                    ledger, scene_num=scene_num, provider=provider,
                    item=item, media_type="video", local_path=scene_video,
                    quality_score=score, license_text=candidate.get("license_text", ""),
                ):
                    scene_video.unlink(missing_ok=True)
                    continue
                vid = item.get("id")
                if vid:
                    used_ids.add(vid)
                return {
                    "saved": True,
                    "media_type": "video",
                    "source": f"{provider}:{query}",
                    "provedor": provider,
                    "query_enriched": query,
                    "quality_score": round(score, 3),
                    "visual_score": candidate.get("visual_score", 0),
                    "visual_breakdown": candidate.get("visual_breakdown"),
                    "visual_fallbacks": fallbacks,
                    "orchestrator_rank": rank,
                    "candidates_evaluated": len(scored_candidates),
                    "selection_signature": selection_signature(item, "video", provider),
                    "width": item.get("width", 0),
                    "height": item.get("height", 0),
                }
        elif _download_scene_photo(item, scene_image):
            if not _register_asset_in_ledger(
                ledger, scene_num=scene_num, provider=provider,
                item=item, media_type="photo", local_path=scene_image,
                quality_score=score, license_text=candidate.get("license_text", ""),
            ):
                scene_image.unlink(missing_ok=True)
                continue
            pid = item.get("id")
            if pid:
                used_ids.add(pid)
            return {
                "saved": True,
                "media_type": "image",
                "source": f"{provider}:{query}",
                "provedor": provider,
                "query_enriched": query,
                "quality_score": round(score, 3),
                "visual_score": candidate.get("visual_score", 0),
                "visual_breakdown": candidate.get("visual_breakdown"),
                "visual_fallbacks": fallbacks,
                "orchestrator_rank": rank,
                "candidates_evaluated": len(scored_candidates),
                "selection_signature": selection_signature(item, "photo", provider),
                "width": item.get("width", 0),
                "height": item.get("height", 0),
            }

    return None


def _resolve_scene_media(
    scene_num: int,
    query_item: dict,
    scene_video: Path,
    scene_image: Path,
    used_ids: set,
    saved_assets: list[Path] | None = None,
    recent_selections: list | None = None,
    rejections: RejectionLog | None = None,
    subject: dict | None = None,
    scene: dict | None = None,
    ledger: AssetRightsLedger | None = None,
    t2v_tracker: T2VTracker | None = None,
) -> dict:
    """Resolve mídia para uma cena com fallback completo."""

    busca = query_item.get("busca", "")
    fallback = query_item.get("busca_fallback", "")
    tematica = query_item.get("busca_tematica", "")
    atmosfera = query_item.get("busca_atmosfera", "")
    tipo = query_item.get("tipo", "")
    preferir_imagem = query_item.get("preferir_imagem", False)
    visual_direction = query_item.get("visual_direction")
    critical_scene = is_critical_scene(tipo)
    allow_pollinations = not critical_scene

    result = {
        "scene": scene_num,
        "tipo": tipo,
        "query": busca,
        "query_enriched": busca,
        "source": "none",
        "provedor": "none",
        "media_type": "none",
        "saved": False,
        "quality_score": 0.0,
        "preferir_imagem": preferir_imagem,
        "critical_scene": critical_scene,
    }

    scene = scene or {}
    topic = (subject or {}).get("nome", "")
    platform = (subject or {}).get("_output_platform", "youtube_dark")

    # --- Prioridade 1: Media Search Orchestrator (footage-first) ---
    orchestrated = _try_orchestrated_stock(
        scene_num, query_item, scene, scene_video, scene_image, used_ids,
        topic=topic,
        prefer_image=preferir_imagem,
        recent_selections=recent_selections,
        rejections=rejections,
        ledger=ledger,
    )
    if orchestrated:
        result.update(orchestrated)
        result["scene"] = scene_num
        result["tipo"] = tipo
        label = "vídeo" if orchestrated["media_type"] == "video" else "imagem"
        print(
            f"🎬 Cena {scene_num} ({tipo}): {label} stock orquestrado "
            f"(score {orchestrated['quality_score']}) — {orchestrated['provedor']}"
        )
        return result

    search_queries = _enrich_search_query(
        busca, tipo, fallback, tematica=tematica, atmosfera=atmosfera
    )

    media_by_query: dict[str, tuple[dict, str]] = {}
    for query in search_queries:
        media_by_query[query] = _search_all_providers(
            query,
            photos_only=preferir_imagem,
            query_item=query_item,
        )

    stock_video_found = False

    if not preferir_imagem:
        for query in search_queries:
            media, source = media_by_query[query]
            if not media.get("videos"):
                continue

            top_score = best_video_score(query, media.get("videos", []), used_ids)
            if top_score < MIN_RELEVANCE_SCORE:
                print(
                    f"  ⚠️ Cena {scene_num}: relevância baixa ({top_score:.2f}) "
                    f"para '{query}' — ignorando resultados genéricos"
                )
                if rejections:
                    rejections.record(
                        scene=scene_num, score=top_score,
                        rejected_reason="generic_content", provider=source, query=query,
                    )
                continue

            saved, chosen, quality_score = _try_stock_videos(
                query, media, scene_video, used_ids, query_item, source,
                recent_selections=recent_selections,
                rejections=rejections,
                scene_num=scene_num,
            )
            if saved and chosen:
                vid = chosen.get("id")
                if vid:
                    used_ids.add(vid)
                stock_video_found = True
                result.update({
                    "saved": True,
                    "media_type": "video",
                    "source": f"{source}:{query}",
                    "provedor": source,
                    "query_enriched": query,
                    "quality_score": quality_score,
                    "selection_signature": selection_signature(chosen, "video", source),
                })
                print(
                    f"🎬 Cena {scene_num} ({tipo}): vídeo HD "
                    f"(score {quality_score}) — {source}"
                )
                return result

    if not stock_video_found:
        for query in search_queries:
            media, source = media_by_query[query]
            if not media.get("photos"):
                continue

            top_photo_score = max(
                (score_photo(query, photo) for photo in media.get("photos", [])),
                default=0.0,
            )
            if top_photo_score < MIN_PHOTO_RELEVANCE_SCORE:
                print(
                    f"  ⚠️ Cena {scene_num}: fotos irrelevantes para '{query}' "
                    f"(score {top_photo_score:.2f})"
                )
                if rejections:
                    rejections.record(
                        scene=scene_num, score=top_photo_score,
                        rejected_reason="generic_content", provider=source, query=query,
                    )
                continue

            saved, chosen = _try_stock_photos(
                query, media, scene_image, used_ids, query_item, source,
                recent_selections=recent_selections,
                rejections=rejections,
                scene_num=scene_num,
            )
            if saved and chosen:
                pid = chosen.get("id")
                if pid:
                    used_ids.add(pid)
                result.update({
                    "saved": True,
                    "media_type": "image",
                    "source": f"{source}:{query}",
                    "provedor": source,
                    "query_enriched": query,
                    "quality_score": round(score_photo(query, chosen), 3),
                    "selection_signature": selection_signature(chosen, "photo", source),
                })
                print(f"🖼️ Cena {scene_num} ({tipo}): imagem stock — {source}")
                return result

    stock_failed = not result.get("saved")

    # --- Prioridade 2: Fallback editorial (Ken Burns, motion graphics) ---
    if stock_failed:
        print(f"  📐 Cena {scene_num}: tentando fallback editorial...")
        duration = float(scene.get("duration_seconds", 5) or 5)
        saved_images = [p for p in (saved_assets or []) if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
        editorial_ok, editorial_type, strategy = execute_editorial_fallback(
            scene, query_item,
            scene_image=scene_image,
            scene_video=scene_video,
            saved_images=saved_images,
            duration=min(duration, 12),
        )
        if editorial_ok:
            if ledger:
                ledger.register_asset(
                    source="generated",
                    provider="generated",
                    license_text="Editorial composite",
                    media_type=editorial_type,
                    scene_id=scene_num,
                    local_path=scene_video,
                    visual_quality_score=0.75,
                )
            result.update({
                "saved": True,
                "media_type": editorial_type,
                "source": f"editorial:{strategy}",
                "provedor": "generated",
                "quality_score": 0.75,
                "fallback_strategy": strategy,
            })
            print(f"📐 Cena {scene_num} ({tipo}): fallback editorial — {strategy}")
            return result

    # --- Prioridade 3: T2V seletivo (máx. 2 cenas) ---
    if stock_failed and not result.get("saved"):
        tracker = t2v_tracker or T2VTracker()
        if preferir_imagem:
            print(
                f"  💰 Cena {scene_num}: preferir_imagem — "
                f"pulando T2V (imagem + Ken Burns, estilo template n8n)"
            )
            t2v_decision = T2VDecision(
                should_use_t2v=False,
                reason="preferir_imagem",
            )
        elif not _t2v_budget_available() or not tracker.can_use_t2v():
            print(
                f"  💰 Cena {scene_num}: orçamento T2V esgotado "
                f"({MAX_T2V_SCENES_PER_VIDEO}/vídeo) — usando imagem + Ken Burns"
            )
            t2v_decision = T2VDecision(
                should_use_t2v=False,
                reason="t2v_budget_exhausted",
            )
        else:
            t2v_decision = evaluate_t2v_decision(
                scene_num, scene, query_item,
                tracker=tracker,
                stock_failed=True,
                editorial_failed=True,
                scene_importance=0.8 if critical_scene else 0.5,
            )
        result["t2v_decision"] = t2v_decision.to_dict()

        if not t2v_decision.should_use_t2v:
            print(f"  ⏭️ Cena {scene_num}: T2V skipped — {t2v_decision.reason}")
        else:
            print(f"  ⚠️ Cena {scene_num}: T2V aprovado — {t2v_decision.reason}")
            image_url = None
            product_name = None
            category = None
            material = None
            if subject:
                image_url = subject.get("image_url") or subject.get("imagem_url")
                product_name = subject.get("nome") or subject.get("name")
                category = subject.get("categoria") or subject.get("category")
                material = subject.get("material")

            scene_description = query_item.get("visual_goal", busca)
            emotion = query_item.get("emotion", "")

            ai_video_saved = False
            ai_video_provider = ""

            i2v_ecommerce = (
                image_url
                and (fal_kling_is_configured() or replicate_is_configured())
                and product_name
            )
            if i2v_ecommerce:
                ai_video_saved, ai_video_provider = _try_ai_video(
                    busca, scene_video,
                    image_url=image_url, product_name=product_name,
                    category=category, material=material,
                    scene_description=scene_description, scene_tipo=tipo,
                    emotion=emotion, platform=platform,
                    visual_direction=visual_direction,
                    allow_pollinations=allow_pollinations,
                )
            elif use_n8n_for_scenes():
                print(f"[n8n] delegando T2V cena {scene_num} ao orquestrador n8n")
                n8n_result = generate_scene_video_fallback(
                    scene_description=scene_description,
                    scene_query=t2v_decision.prompt or busca,
                    output_path=scene_video,
                    platform=platform,
                    scene_tipo=tipo,
                    emotion=emotion,
                    scene=query_item,
                )
                if n8n_result and n8n_result.get("local_path"):
                    ai_video_saved = True
                    ai_video_provider = n8n_result.get("api_used", "n8n")
            else:
                ai_video_saved, ai_video_provider = _try_ai_video(
                    busca, scene_video,
                    image_url=image_url, product_name=product_name,
                    category=category, material=material,
                    scene_description=scene_description, scene_tipo=tipo,
                    emotion=emotion, platform=platform,
                    visual_direction=visual_direction,
                    allow_pollinations=allow_pollinations,
                )

            if ai_video_saved:
                _consume_t2v_budget()
                tracker.record_use(scene_num, t2v_decision)
                if ledger:
                    ledger.register_asset(
                        source=ai_video_provider,
                        provider=ai_video_provider,
                        license_text="AI generated (T2V)",
                        media_type="t2v",
                        scene_id=scene_num,
                        local_path=scene_video,
                        visual_quality_score=0.55,
                    )
                result.update({
                    "saved": True,
                    "media_type": "ai_video",
                    "source": f"{ai_video_provider}:video",
                    "provedor": ai_video_provider,
                    "quality_score": 0.55,
                })
                label = ai_video_provider if ai_video_provider != "pollinations" else "Pollinations"
                print(f"🤖 Cena {scene_num} ({tipo}): vídeo T2V {label}")
                return result

            print(f"  ⚠️ Cena {scene_num}: T2V falhou — fallback editorial")
            fb_ok, fb_type, fb_strategy = execute_editorial_fallback(
                scene, query_item,
                scene_image=scene_image, scene_video=scene_video,
                saved_images=[p for p in (saved_assets or []) if p.suffix.lower() in {".jpg", ".jpeg", ".png"}],
            )
            if fb_ok:
                result.update({
                    "saved": True,
                    "media_type": fb_type,
                    "source": f"editorial:{fb_strategy}",
                    "provedor": "generated",
                    "quality_score": 0.70,
                    "t2v_fallback": True,
                })
                print(f"📐 Cena {scene_num} ({tipo}): fallback pós-T2V — {fb_strategy}")
                return result

    # --- Prioridade 4: Imagem IA documental ---
    ai_saved, ai_provider = _try_ai_image(
        busca,
        scene_image,
        allow_upscale=True,
        allow_pollinations=allow_pollinations,
        scene_description=query_item.get("visual_goal", query_item.get("visual", busca)),
        scene_tipo=tipo,
        emotion=query_item.get("emotion", ""),
        platform=platform,
        visual_direction=visual_direction,
    )
    if ai_saved:
        result.update({
            "saved": True,
            "media_type": "ai_image",
            "source": f"{ai_provider}:image",
            "provedor": ai_provider,
        })
        provider_labels = {
            "pollinations": "Pollinations",
            "replicate_flux": "Replicate Flux",
            "huggingface": "Hugging Face",
        }
        label = provider_labels.get(ai_provider, ai_provider)
        print(f"🤖 Cena {scene_num} ({tipo}): imagem {label}")
        return result

    ai_retry_saved, ai_retry_provider = _try_ai_image(
        busca,
        scene_image,
        ", atmospheric wide establishing shot, epic scale",
        allow_upscale=True,
        allow_pollinations=allow_pollinations,
        scene_description=query_item.get("visual_goal", query_item.get("visual", busca)),
        scene_tipo=tipo,
        emotion=query_item.get("emotion", ""),
        platform=platform,
        visual_direction=visual_direction,
    )
    if ai_retry_saved:
        result.update({
            "saved": True,
            "media_type": "ai_image_retry",
            "source": f"{ai_retry_provider}:image:retry",
            "provedor": ai_retry_provider,
        })
        print(f"🤖 Cena {scene_num} ({tipo}): imagem IA (retry)")
        return result

    if _generate_placeholder_image(
        busca,
        scene_image,
        scene_num,
        allow_pollinations=allow_pollinations,
    ):
        result.update({
            "saved": True,
            "media_type": "placeholder",
            "source": "generated:placeholder",
            "provedor": "generated",
        })
        print(f"🖼️ Cena {scene_num} ({tipo}): imagem ilustrativa gerada")
        return result

    raise RuntimeError(f"Cena {scene_num}: nenhuma mídia disponível após cadeia completa")


def run_visual_media_pipeline(subject, scenes, queries) -> str:
    """
    Pipeline footage-first com orchestrator, rights ledger e T2V seletivo.
    Salva arquivos como scene-01.mp4, scene-02.jpg, etc.
    """

    _reset_t2v_budget()

    folder = _output_folder(subject) / "assets"
    output_root = _output_folder(subject)
    videos_folder = folder / "videos"
    images_folder = folder / "images"
    videos_folder.mkdir(parents=True, exist_ok=True)
    images_folder.mkdir(parents=True, exist_ok=True)

    used_ids: set = set()
    saved_assets: list[Path] = []
    results = []
    rejections = RejectionLog()
    recent_selections: list[dict] = []
    ledger = AssetRightsLedger(output_root)
    t2v_tracker = T2VTracker()

    scene_list = scenes.get("cenas", []) if isinstance(scenes, dict) else []

    for i, query_item in enumerate(queries):
        scene_num = i + 1
        scene_video = videos_folder / f"scene-{scene_num:02d}.mp4"
        scene_image = images_folder / f"scene-{scene_num:02d}.jpg"
        scene_data = scene_list[i] if i < len(scene_list) else {}

        result = _resolve_scene_media(
            scene_num,
            query_item,
            scene_video,
            scene_image,
            used_ids,
            saved_assets=saved_assets,
            recent_selections=recent_selections[-2:],
            rejections=rejections,
            subject=subject,
            scene=scene_data,
            ledger=ledger,
            t2v_tracker=t2v_tracker,
        )

        signature = result.pop("selection_signature", None)
        if signature:
            recent_selections.append(signature)

        results.append(result)

        if result.get("saved"):
            if scene_video.exists():
                saved_assets.append(scene_video)
            elif scene_image.exists():
                saved_assets.append(scene_image)

    ledger.export_report(output_root)

    output = {
        "produto": subject.get("nome", ""),
        "engine": "visual_media_engine",
        "version": 4,
        "architecture": "footage_first",
        "scenes": results,
        "t2v_usage": t2v_tracker.to_dict(),
        "rights_all_safe": ledger.all_safe(),
    }

    with open(folder / "media_search.json", "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=4)

    rejections.flush(folder)

    saved_count = sum(1 for r in results if r["saved"])
    t2v_used = len(t2v_tracker.used_scenes)
    print(
        f"📸 Visual Media Engine: {saved_count}/{len(results)} cenas | "
        f"T2V: {t2v_used}/{t2v_tracker.max_scenes} | "
        f"Rights: {'OK' if ledger.all_safe() else 'UNSAFE'}"
    )

    if saved_count < len(results):
        raise RuntimeError(
            f"Cobertura de mídia insuficiente: {saved_count}/{len(results)} — mínimo 100%"
        )

    return "visual_engine"
