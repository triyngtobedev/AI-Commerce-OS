"""
Validação de qualidade de mídia baixada ou gerada.
"""

from __future__ import annotations

from pathlib import Path

from scripts.video.media_probe import probe_dimensions, probe_duration

MIN_VIDEO_WIDTH = 1920
MIN_VIDEO_HEIGHT = 1080
MIN_VIDEO_WIDTH_FALLBACK = 1280
MIN_VIDEO_HEIGHT_FALLBACK = 720
MIN_VIDEO_DURATION = 5.0
MIN_IMAGE_WIDTH = 1920
MIN_IMAGE_HEIGHT = 1080
MIN_IMAGE_WIDTH_FALLBACK = 1280
MIN_IMAGE_HEIGHT_FALLBACK = 720
MIN_FILE_BYTES = 8000
MIN_VIDEO_FILE_BYTES = 400_000


def is_landscape(width: int, height: int, tolerance: float = 1.15) -> bool:
    """True se orientação é paisagem (16:9 friendly)."""

    if width <= 0 or height <= 0:
        return False
    return width >= height / tolerance


def validate_video_file(
    path: Path,
    *,
    min_width: int = MIN_VIDEO_WIDTH,
    min_height: int = MIN_VIDEO_HEIGHT,
    min_duration: float = MIN_VIDEO_DURATION,
    require_landscape: bool = True,
) -> tuple[bool, str]:
    """Valida vídeo local. Retorna (ok, motivo)."""

    media = Path(path)

    if not media.exists():
        return False, "arquivo inexistente"

    size = media.stat().st_size
    if size < MIN_FILE_BYTES:
        return False, f"arquivo muito pequeno ({size} bytes)"

    if size < MIN_VIDEO_FILE_BYTES:
        return False, f"bitrate baixo / arquivo comprimido demais ({size} bytes)"

    width, height = probe_dimensions(media)
    if width < min_width or height < min_height:
        return False, f"resolução baixa ({width}x{height})"

    if require_landscape and not is_landscape(width, height):
        return False, f"orientação vertical ({width}x{height})"

    duration = probe_duration(media)
    if duration < min_duration:
        return False, f"duração curta ({duration:.1f}s)"

    return True, "ok"


def validate_image_file(
    path: Path,
    *,
    min_width: int = MIN_IMAGE_WIDTH,
    min_height: int = MIN_IMAGE_HEIGHT,
) -> tuple[bool, str]:
    """Valida imagem local. Retorna (ok, motivo)."""

    media = Path(path)

    if not media.exists():
        return False, "arquivo inexistente"

    size = media.stat().st_size
    if size < MIN_FILE_BYTES:
        return False, f"arquivo muito pequeno ({size} bytes)"

    width, height = probe_dimensions(media)
    if width < min_width or height < min_height:
        return False, f"resolução baixa ({width}x{height})"

    return True, "ok"


def resolution_score(width: int, height: int) -> float:
    """Pontua resolução normalizada (0–1) para 1920×1080."""

    if width <= 0 or height <= 0:
        return 0.0

    pixels = width * height
    base = min(1.0, pixels / (1920 * 1080))

    if width >= 3840 and height >= 2160:
        return min(1.0, base + 0.15)

    if width >= 1920 and height >= 1080:
        return base

    if width >= MIN_VIDEO_WIDTH_FALLBACK and height >= MIN_VIDEO_HEIGHT_FALLBACK:
        return base * 0.65

    return base * 0.3
