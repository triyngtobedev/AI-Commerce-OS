"""
Pipeline compartilhado de mídia.

Extrai lógica de busca/download de mídia reutilizável
entre pipelines TikTok e YouTube.
"""

from scripts.video.asset_manager import clear_media_assets
from scripts.video.media_search import search_media
from scripts.video.media_downloader import download_videos
from scripts.video.visual_media_engine import run_visual_media_pipeline
from scripts.video.pollinations_media_pipeline import (
    generate_persona_media,
    should_use_persona,
)


def _run_stock_or_visual(subject, scenes, queries, platform):
    """Pipeline padrão: Visual Media Engine (YouTube) ou stock (demais)."""

    if platform == "youtube_dark":
        # TODO: hook para geração de vídeo IA (Veo/Kling) em cenas hero
        print("📸 Visual Media Engine ativado (scene-aware + fallback IA).")
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
