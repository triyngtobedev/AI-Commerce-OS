"""
Visual Media Engine — busca e geração de mídia por cena.

Cadeia de fallback por cena (youtube_dark):
  1. Wikimedia Commons — imagens de arquivo/domínio público
  2. Pixabay — vídeo/foto stock HD
  3. Pexels — vídeo/foto stock (fallback legado)
  4. Pollinations IA — imagem gratuita (primário IA)
  5. Hugging Face SDXL — imagem (fallback se HF_TOKEN configurado)
  6. Pollinations IA — vídeo (se POLLINATIONS_API_KEY configurada)
  7. Pollinations IA — segunda tentativa de imagem com prompt alternativo

Cenas documentais (contexto, desenvolvimento, revelacao, consequencias)
com preferir_imagem=True pulam busca de vídeo e usam foto + Ken Burns.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from scripts.video.pexels_provider import search_pexels
from scripts.video.pixabay_provider import search_pixabay
from scripts.video.wikimedia_provider import search_wikimedia
from scripts.video.media_providers.pollinations_provider import (
    generate_pollinations_image,
    generate_pollinations_video,
)
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


def _enrich_search_query(busca: str, tipo: str, fallback: str = "") -> list[str]:
    """
    Gera variações de busca cinematográficas baseadas na cena.
    Retorna queries em ordem de prioridade (sem duplicatas).
    """

    queries = []
    base = _truncate_query(busca.strip())
    if base:
        queries.append(base)

    suffix = _CINEMATIC_SUFFIX.get(tipo, "documentary cinematic")
    if base:
        enriched = _truncate_query(f"{base} {suffix}")
        if enriched not in queries:
            queries.append(enriched)

    if fallback:
        fallback_query = _truncate_query(fallback.strip())
        if fallback_query and fallback_query not in queries:
            queries.append(fallback_query)

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


def _search_providers_chain(query: str, *, photos_only: bool = False) -> tuple[dict, str]:
    """Busca Wikimedia → Pixabay → Pexels até encontrar mídia."""

    query = _truncate_query(query)

    for provider_name, search_fn in (
        ("wikimedia", search_wikimedia),
        ("pixabay", search_pixabay),
        ("pexels", search_pexels),
    ):
        media = search_fn(query)
        if photos_only:
            media = {"videos": [], "photos": media.get("photos", [])}
        if _has_media(media):
            return media, provider_name

    return {"videos": [], "photos": []}, "none"


def _search_all_providers(query: str, *, photos_only: bool = False) -> tuple[dict, str]:
    """Alias legado — cadeia ordenada de provedores."""

    return _search_providers_chain(query, photos_only=photos_only)


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


def _try_ai_image(
    prompt: str,
    scene_image: Path,
    suffix: str = "",
    *,
    allow_upscale: bool = True,
) -> tuple[bool, str]:
    ai_prompt = _truncate_query(f"{prompt}, documentary cinematic scene{suffix}", max_len=120)
    provider = ""
    generated = generate_pollinations_image(ai_prompt, scene_image)
    if generated:
        provider = "pollinations"
    elif _try_hf_image(ai_prompt, scene_image):
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


def _generate_placeholder_image(prompt: str, scene_image: Path, scene_num: int) -> bool:
    """Gera imagem ilustrativa mínima quando todos os provedores falham."""

    label = _truncate_query(prompt or f"scene {scene_num}", max_len=40)
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
        saved, _ = _try_ai_image(
            f"{prompt}, atmospheric documentary illustration",
            scene_image,
            allow_upscale=True,
        )
        return saved


def _try_ai_video(prompt: str, scene_video: Path) -> bool:
    ai_prompt = f"{prompt}, documentary cinematic footage"
    generated = generate_pollinations_video(ai_prompt, scene_video)
    if not generated:
        return False

    valid, reason = validate_video_file(scene_video, min_duration=2.0)
    if not valid:
        print(f"  ⚠️ Vídeo IA rejeitado ({reason})")
        if scene_video.exists():
            scene_video.unlink()
        return False

    return True


def _resolve_scene_media(
    scene_num: int,
    query_item: dict,
    scene_video: Path,
    scene_image: Path,
    used_ids: set,
    saved_assets: list[Path] | None = None,
    recent_selections: list | None = None,
    rejections: RejectionLog | None = None,
) -> dict:
    """Resolve mídia para uma cena com fallback completo."""

    busca = query_item.get("busca", "")
    fallback = query_item.get("busca_fallback", "")
    tipo = query_item.get("tipo", "")
    preferir_imagem = query_item.get("preferir_imagem", False)

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
    }

    search_queries = _enrich_search_query(busca, tipo, fallback)

    media_by_query: dict[str, tuple[dict, str]] = {}
    for query in search_queries:
        media_by_query[query] = _search_all_providers(
            query,
            photos_only=preferir_imagem,
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

    ai_saved, ai_provider = _try_ai_image(busca, scene_image, allow_upscale=True)
    if ai_saved:
        result.update({
            "saved": True,
            "media_type": "ai_image",
            "source": f"{ai_provider}:image",
            "provedor": ai_provider,
        })
        label = "Pollinations" if ai_provider == "pollinations" else "Hugging Face"
        print(f"🤖 Cena {scene_num} ({tipo}): imagem {label}")
        return result

    if not preferir_imagem and _try_ai_video(busca, scene_video):
        result.update({"saved": True, "media_type": "ai_video", "source": "pollinations:video", "provedor": "pollinations"})
        print(f"🤖 Cena {scene_num} ({tipo}): vídeo Pollinations")
        return result

    ai_retry_saved, ai_retry_provider = _try_ai_image(
        f"{busca}, {tipo}", scene_image, ", atmospheric wide shot", allow_upscale=True
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

    if _generate_placeholder_image(busca, scene_image, scene_num):
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
    Pipeline de mídia scene-aware com seleção por relevância e fallback IA.
    Salva arquivos como scene-01.mp4, scene-02.jpg, etc.
    """

    folder = _output_folder(subject) / "assets"
    videos_folder = folder / "videos"
    images_folder = folder / "images"
    videos_folder.mkdir(parents=True, exist_ok=True)
    images_folder.mkdir(parents=True, exist_ok=True)

    used_ids: set = set()
    saved_assets: list[Path] = []
    results = []
    rejections = RejectionLog()
    # Histórico das cenas anteriores (comparação com as 2 últimas).
    recent_selections: list[dict] = []

    for i, query_item in enumerate(queries):
        scene_num = i + 1
        scene_video = videos_folder / f"scene-{scene_num:02d}.mp4"
        scene_image = images_folder / f"scene-{scene_num:02d}.jpg"

        result = _resolve_scene_media(
            scene_num,
            query_item,
            scene_video,
            scene_image,
            used_ids,
            saved_assets=saved_assets,
            recent_selections=recent_selections[-2:],
            rejections=rejections,
        )

        # Assinatura de diversidade é transiente: alimenta o histórico e é
        # removida antes de serializar para não alterar a estrutura de output.
        signature = result.pop("selection_signature", None)
        if signature:
            recent_selections.append(signature)

        results.append(result)

        if result.get("saved"):
            if scene_video.exists():
                saved_assets.append(scene_video)
            elif scene_image.exists():
                saved_assets.append(scene_image)

    output = {
        "produto": subject.get("nome", ""),
        "engine": "visual_media_engine",
        "version": 3,
        "scenes": results,
    }

    with open(folder / "media_search.json", "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=4)

    # Log de auditoria de rejeições (best-effort, fora do contrato).
    rejections.flush(folder)

    saved_count = sum(1 for r in results if r["saved"])
    print(f"📸 Visual Media Engine: {saved_count}/{len(results)} cenas com mídia")

    if saved_count < len(results):
        raise RuntimeError(
            f"Cobertura de mídia insuficiente: {saved_count}/{len(results)} — mínimo 100%"
        )

    return "visual_engine"
