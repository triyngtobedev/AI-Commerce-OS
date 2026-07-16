"""
Overlays de marca para thumbnails e vídeo.

Delega layout de thumbnail ao BrandKit; mantém filtros FFmpeg para vídeo.
"""

from pathlib import Path
from typing import Optional

from scripts.core.brand_kit import get_brand_kit
from scripts.core.brand_profile import BrandProfile, get_brand


def apply_brand_thumbnail(
    image_path: Path,
    hook_text: str,
    output_path: Path,
    brand: Optional[BrandProfile] = None,
    subtitle: str = "",
    platform: str = "youtube_dark",
) -> bool:
    """Aplica layout CTR via BrandKit."""

    kit = get_brand_kit(platform)
    return kit.compose_thumbnail(
        image_path,
        hook_text,
        output_path,
        topic=subtitle,
    )


def watermark_filter(
    brand: Optional[BrandProfile] = None,
    platform: str = "youtube_dark",
) -> str:
    """Retorna filtro FFmpeg drawtext para marca d'água discreta."""

    kit = get_brand_kit(platform)
    return kit.watermark_filter()


def lower_third_filter(
    text: str,
    duration: float,
    platform: str = "youtube_dark",
) -> str:
    """Retorna filtro FFmpeg para lower third de cena."""

    kit = get_brand_kit(platform)
    return kit.lower_third_filter(text, duration)
