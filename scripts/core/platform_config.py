"""
Configurações de plataforma para o AI-Commerce-OS.

Centraliza parâmetros específicos de cada destino de publicação,
permitindo que engines compartilhados se comportem de forma diferente
sem duplicar lógica de negócio.
"""

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass(frozen=True)
class RenderProfile:
    """Perfil de renderização de vídeo."""

    width: int
    height: int
    aspect_label: str


@dataclass(frozen=True)
class PlatformConfig:
    """
    Perfil completo de uma plataforma de publicação.

    Attributes:
        id: Identificador único (tiktok_shop, youtube_dark)
        label: Nome legível
        content_type: Tipo de input (product, topic)
        render: Dimensões de saída
        scene_count: Número padrão de cenas
        target_duration_seconds: Duração alvo do vídeo
        narration_style: Estilo de narração para prompts
        monetization_model: Modelo de receita principal
    """

    id: str
    label: str
    content_type: str
    render: RenderProfile
    scene_count: int
    target_duration_seconds: int
    narration_style: str
    monetization_model: str
    formato: str
    cta_template: str
    cache_prefix: str = ""
    extra_metadata_fields: List[str] = field(default_factory=list)


# Perfis pré-definidos
TIKTOK_SHOP = PlatformConfig(
    id="tiktok_shop",
    label="TikTok Shop",
    content_type="product",
    render=RenderProfile(1080, 1920, "9:16"),
    scene_count=4,
    target_duration_seconds=30,
    narration_style="review_ugc_curto",
    monetization_model="afiliado",
    formato="video_vertical_tiktok_shop",
    cta_template="Link na bio do TikTok Shop",
    cache_prefix="tiktok",
)

YOUTUBE_DARK = PlatformConfig(
    id="youtube_dark",
    label="YouTube Dark (História & Curiosidades)",
    content_type="topic",
    render=RenderProfile(1920, 1080, "16:9"),
    scene_count=8,
    target_duration_seconds=480,
    narration_style="documentario_narrado",
    monetization_model="adsense",
    formato="video_horizontal_youtube_documentario",
    cta_template="Inscreva-se e ative o sininho",
    cache_prefix="youtube",
    extra_metadata_fields=[
        "tags",
        "capitulos",
        "thumbnail_texto",
        "categoria_youtube",
    ],
)

PLATFORMS = {
    "tiktok_shop": TIKTOK_SHOP,
    "youtube_dark": YOUTUBE_DARK,
}


def get_platform(platform_id: str) -> PlatformConfig:
    """Retorna configuração da plataforma ou levanta erro."""

    config = PLATFORMS.get(platform_id)

    if not config:
        available = ", ".join(PLATFORMS.keys())
        raise ValueError(
            f"Plataforma desconhecida: {platform_id}. "
            f"Disponíveis: {available}"
        )

    return config


def get_render_dimensions(platform: PlatformConfig) -> Tuple[int, int]:
    """Retorna (width, height) para renderização."""

    return platform.render.width, platform.render.height
