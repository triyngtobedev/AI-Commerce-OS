"""
Brand Engine — identidade visual consistente para YouTube Dark.

Integra BrandKit com estilos de legenda, watermark, transições e abertura/encerramento.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from scripts.core.brand_kit import BrandKit, get_brand_kit
from scripts.core.brand_profile import BrandProfile, get_brand


@dataclass(frozen=True)
class SubtitleStyle:
    font_name: str = "Arial"
    font_size: int = 16
    margin_v: int = 70
    outline: int = 2
    shadow: int = 2
    max_words_per_block: int = 5
    max_chars: int = 42
    bold: bool = True
    highlight_colors: tuple = ("gold", "red", "cyan")


@dataclass(frozen=True)
class RenderStyle:
    transition_seconds: float = 0.7
    crossfade_seconds: float = 0.3
    ken_burns_zoom_max: float = 1.04
    color_grade: str = (
        "eq=contrast=1.15:brightness=-0.02:saturation=0.80,"
        "colorbalance=rs=-0.03:gs=0:bs=0.05"
    )
    vignette: str = "vignette=angle=PI/3:mode=forward"
    opening_fade_seconds: float = 0.8
    closing_fade_seconds: float = 2.0
    intro_seconds: float = 2.0
    outro_seconds: float = 2.5
    film_grain: str = "noise=alls=8:allf=t+u"
    bgm_volume: float = 0.10
    bgm_tension_volume: float = 0.15


@dataclass(frozen=True)
class BrandEngineConfig:
    brand: BrandProfile
    kit: BrandKit
    subtitle: SubtitleStyle
    render: RenderStyle
    show_watermark: bool = True
    show_intro: bool = True
    show_outro: bool = True
    show_lower_thirds: bool = True
    opening_style: str = "branded_card"
    closing_style: str = "branded_card_fade"


def _build_config(platform_id: str) -> BrandEngineConfig:
    kit = get_brand_kit(platform_id)
    cinematic = kit.cinematic

    return BrandEngineConfig(
        brand=kit.profile,
        kit=kit,
        subtitle=SubtitleStyle(
            font_name="Arial",
            font_size=52,
            margin_v=110,
            outline=2,
            shadow=2,
            max_words_per_block=5,
            max_chars=42,
            bold=True,
            highlight_colors=("gold", "red", "cyan"),
        ),
        render=RenderStyle(
            transition_seconds=cinematic.transition_seconds,
            crossfade_seconds=cinematic.crossfade_seconds,
            ken_burns_zoom_max=cinematic.ken_burns_zoom_max,
            color_grade=cinematic.color_grade,
            vignette=cinematic.vignette,
            opening_fade_seconds=cinematic.opening_fade_seconds,
            closing_fade_seconds=cinematic.closing_fade_seconds,
            intro_seconds=kit.overlay.intro_seconds,
            outro_seconds=kit.overlay.outro_seconds,
            film_grain=cinematic.film_grain,
            bgm_volume=cinematic.bgm_volume,
            bgm_tension_volume=cinematic.bgm_tension_volume,
        ),
        show_watermark=True,
        show_intro=True,
        show_outro=True,
        show_lower_thirds=True,
    )


YOUTUBE_DARK_CONFIG = _build_config("youtube_dark")


def get_brand_config(platform_id: str = "youtube_dark") -> BrandEngineConfig:
    if platform_id == "youtube_dark":
        return YOUTUBE_DARK_CONFIG
    return _build_config(platform_id)


def get_brand_kit_for_platform(platform_id: str = "youtube_dark") -> BrandKit:
    return get_brand_config(platform_id).kit


def get_subtitle_style(platform_id: str = "youtube_dark") -> dict:
    config = get_brand_config(platform_id)
    style = config.subtitle

    return {
        "font_name": style.font_name,
        "font_size": style.font_size,
        "margin_v": style.margin_v,
        "outline": style.outline,
        "shadow": style.shadow,
        "max_words_per_block": style.max_words_per_block,
        "max_chars": style.max_chars,
        "bold": style.bold,
        "highlight_colors": style.highlight_colors,
    }


def get_render_style(platform_id: str = "youtube_dark") -> RenderStyle:
    return get_brand_config(platform_id).render


def should_show_watermark(platform_id: str = "youtube_dark") -> bool:
    return get_brand_config(platform_id).show_watermark


def should_show_intro(platform_id: str = "youtube_dark") -> bool:
    return get_brand_config(platform_id).show_intro


def should_show_outro(platform_id: str = "youtube_dark") -> bool:
    return get_brand_config(platform_id).show_outro


def should_show_lower_thirds(platform_id: str = "youtube_dark") -> bool:
    return get_brand_config(platform_id).show_lower_thirds


def watermark_filter_for_platform(platform_id: str = "youtube_dark") -> Optional[str]:
    if not should_show_watermark(platform_id):
        return None

    from scripts.youtube.brand_overlay import watermark_filter

    return watermark_filter(platform=platform_id)
