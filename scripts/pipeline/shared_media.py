"""
Pipeline compartilhado de mídia.

Extrai lógica de busca/download de mídia reutilizável
entre pipelines TikTok e YouTube.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from scripts.video.asset_manager import clear_media_assets
from scripts.video.media_search import search_media
from scripts.video.media_downloader import download_videos
from scripts.video.visual_media_engine import run_visual_media_pipeline
from scripts.video.pollinations_media_pipeline import (
    generate_persona_media,
    should_use_persona,
)
from scripts.video.pexels_provider import search_pexels
from scripts.video.media_quality import (
    MIN_VIDEO_HEIGHT_FALLBACK,
    MIN_VIDEO_WIDTH_FALLBACK,
    validate_video_file,
)
from scripts.core.visual_director_engine import direct_scene_visual
from scripts.video.query_localizer import localize_search_query
from src.video_upscaler import upscale_video_ffmpeg
from src.prompt_builder import build_scene_video_prompt
from src.video_generator import (
    VideoGenerator,
    falai_is_configured,
    replicate_is_configured,
    kling_web_is_configured,
)

# Custo estimado por geração T2V no Replicate (LTX trial — ajustável via env).
REPLICATE_ESTIMATED_COST_USD = 0.05


def _ai_video_configured() -> bool:
    return falai_is_configured() or replicate_is_configured() or kling_web_is_configured()


def search_pexels_for_scene(query: str) -> dict | None:
    """
    Busca mídia no Pexels para uma cena.
    Retorna dict com videos/photos ou None se vazio.
    """
    if not query.strip():
        return None

    media = search_pexels(query, orientation="landscape")
    if media.get("erro"):
        print(f"[Pexels] Erro: {media['erro']}")
        return None

    if media.get("videos") or media.get("photos"):
        return media

    print(f"[Pexels] Nenhum resultado para: {query}")
    return None


def _generate_scene_video_fallback_local(
    scene_description: str,
    scene_query: str,
    output_path: Path,
    *,
    platform: str = "youtube",
    scene_tipo: str = "",
    emotion: str = "",
    style: str = "dark, cinematic, dramatic lighting, documentary",
    scene: dict | None = None,
) -> dict | None:
    """
    Gera vídeo T2V via VideoGenerator quando stock (Pexels) falha.
    Cadeia interna: fal.ai → Replicate → Kling Web.
    """
    if not _ai_video_configured():
        print("[VideoGenerator] Nenhuma API de vídeo configurada — fallback IA ignorado")
        return None

    prompt_bundle = build_scene_video_prompt(
        scene_description=scene_description,
        scene_query=localize_search_query(scene_query),
        platform=platform,
        style=style,
        scene_tipo=scene_tipo,
        emotion=emotion,
        visual_direction=(scene or {}).get("visual_direction"),
    )

    api_hint = "Replicate" if replicate_is_configured() else "fal.ai/Kling"
    print(f"[Replicate] tentando T2V via {api_hint}...")
    print(f"  Query: {scene_query[:72]}")

    try:
        scene_ctx = scene if scene is not None else {
            "narracao": scene_description,
            "text": scene_description,
            "visual": scene_description,
            "query": scene_query,
            "tipo": scene_tipo,
            "emotion": emotion,
        }
        visual_dir = direct_scene_visual(scene_ctx).to_dict()
        generator = VideoGenerator(output_dir=output_path.parent)
        result = generator.generate_youtube_scene(
            scene_description=scene_ctx.get("narracao", scene_ctx.get("text", "")),
            scene_query=localize_search_query(scene_query),
            visual_direction=visual_dir,
            download=True,
        )
    except Exception as error:
        print(f"[Replicate] falhou: {error}")
        return None

    local_path = result.get("local_path")
    api_used = result.get("api_used", "unknown")
    resolution = result.get("resolution", "—")
    elapsed = round(result.get("duration_seconds", 0), 1)

    if api_used == "replicate":
        print(f"[Replicate] sucesso — {local_path}")
        print(f"  Resolução: {resolution} | Tempo: {elapsed}s | Custo est.: ~${REPLICATE_ESTIMATED_COST_USD:.2f}")
    else:
        print(f"[VideoGenerator] sucesso via {api_used}: {local_path}")
        print(f"  Resolução: {resolution} | Tempo: {elapsed}s")

    if not local_path or not Path(local_path).exists():
        return None

    src = Path(local_path)
    if src.resolve() != output_path.resolve():
        shutil.copy2(src, output_path)

    try:
        upscaled = upscale_video_ffmpeg(str(output_path), scale=2)
        upscaled_path = Path(upscaled)
        if upscaled_path.exists() and upscaled_path.resolve() != output_path.resolve():
            upscaled_path.replace(output_path)
    except Exception as error:
        print(f"[VideoGenerator] Upscale ignorado: {error}")

    valid = False
    reason = "validacao falhou"
    for min_w, min_h, min_d in (
        (MIN_VIDEO_WIDTH_FALLBACK, MIN_VIDEO_HEIGHT_FALLBACK, 2.0),
        (640, 360, 2.0),
    ):
        valid, reason = validate_video_file(
            output_path,
            min_width=min_w,
            min_height=min_h,
            min_duration=min_d,
        )
        if valid:
            break

    if not valid:
        print(f"[VideoGenerator] Video IA rejeitado ({reason})")
        if output_path.exists():
            output_path.unlink()
        return None

    result["local_path"] = str(output_path)
    return result


def resolve_scene_media(
    scene: dict,
    output_dir: Path,
    platform: str = "youtube",
    *,
    scene_num: int = 1,
) -> str | None:
    """
    Tenta Pexels → fallback Replicate via VideoGenerator.
    Retorna path local do vídeo da cena ou None.
    """
    query = scene.get("query") or scene.get("busca", "")
    description = scene.get("description") or scene.get("visual", "")
    scene_tipo = scene.get("tipo", "")
    emotion = scene.get("emotion", "")

    media = search_pexels_for_scene(query)
    if media and media.get("videos"):
        # Stock encontrado — download fica a cargo do Visual Media Engine completo.
        return None

    output_path = Path(output_dir) / "videos" / f"scene-{scene_num:02d}.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = generate_scene_video_fallback(
        scene_description=description,
        scene_query=query,
        output_path=output_path,
        platform=platform,
        scene_tipo=scene_tipo,
        emotion=emotion,
        scene=scene,
    )
    if result and result.get("local_path"):
        return result["local_path"]
    return None


def _run_stock_or_visual(subject, scenes, queries, platform):
    """Pipeline padrão: Visual Media Engine (YouTube) ou stock (demais)."""

    if platform == "youtube_dark":
        print("📸 Visual Media Engine ativado (scene-aware + VideoGenerator IA).")
        clear_media_assets(subject)
        return run_visual_media_pipeline(subject, scenes, queries)

    print("📸 Modo STOCK ativado.")
    clear_media_assets(subject)
    media = search_media(subject, queries)
    download_videos(subject, media)
    return "stock"


def run_media_pipeline(subject, scenes, queries):
    """
    Executa pipeline de mídia (stock, visual engine ou persona/IA).

    Com CONTENT_MODE=persona (ou "ai"/"pollinations"), gera imagens únicas por
    cena via Pollinations.ai (gratuito) e deixa o render aplicar Ken Burns.
    Caso a IA falhe, faz fallback para o pipeline padrão (visual/stock).

    Retorna:
        "persona", "visual_engine" ou "stock"
    """

    platform = subject.get("_output_platform", "")

    if should_use_persona():

        print("🎨 Modo PERSONA (imagens IA via Pollinations) ativado.")

        persona_images = generate_persona_media(subject, scenes)

        if persona_images:
            print(f"✅ Persona IA: {len(persona_images)} imagem(ns) gerada(s).")
            return "persona"

        total_scenes = len(scenes.get("cenas", []))
        print(
            f"⚠️ Persona IA falhou (0 de {total_scenes} cenas). "
            "Usando pipeline padrão como fallback."
        )

    return _run_stock_or_visual(subject, scenes, queries, platform)


# Wrapper n8n: delega para scene_integration quando USE_N8N_FOR_SCENES=true
from src.n8n_integration.scene_integration import (  # noqa: E402
    generate_scene_video_fallback,
)
