"""
Pipeline compartilhado de mídia.

Extrai lógica de busca/download de mídia reutilizável
entre pipelines TikTok e YouTube.
"""

from scripts.video.asset_manager import clear_media_assets
from scripts.video.media_search import search_media
from scripts.video.media_downloader import download_videos
from scripts.video.persona_media_pipeline import (
    generate_persona_media,
    should_use_persona,
)


def run_media_pipeline(subject, scenes, queries):
    """
    Executa pipeline de mídia (stock ou persona).

    Retorna:
        "persona" ou "stock"
    """

    if not should_use_persona():

        print(
            "📸 Modo STOCK ativado."
        )

        clear_media_assets(subject)

        media = search_media(
            subject,
            queries
        )

        download_videos(
            subject,
            media
        )

        return "stock"

    print(
        "🤖 Modo PERSONA ativado."
    )

    persona_images = generate_persona_media(
        subject,
        scenes
    )

    if persona_images:

        print(
            f"✅ Persona: {len(persona_images)} imagem(ns) gerada(s)."
        )

        return "persona"

    total_scenes = len(
        scenes.get("cenas", [])
    )

    print(
        f"⚠️ Persona falhou (0 de {total_scenes} cenas). "
        "Usando stock como fallback."
    )

    clear_media_assets(subject)

    media = search_media(
        subject,
        queries
    )

    download_videos(
        subject,
        media
    )

    return "stock"
