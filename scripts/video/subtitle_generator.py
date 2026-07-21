import os
from pathlib import Path

from scripts.utils.slug import content_output_dir
from scripts.core.brand_engine import (
    get_render_style,
    should_show_intro,
)
from scripts.video.media_probe import probe_duration
from scripts.video.subtitle_engine import write_subtitles, ffmpeg_subtitle_filter

_DISABLED_LOGGED = False


def subtitles_enabled() -> bool:
    """True quando ENABLE_SUBTITLES=true (padrão: desligado)."""
    return os.getenv("ENABLE_SUBTITLES", "false").lower() in ("true", "1", "yes")


def log_subtitles_disabled_once() -> None:
    global _DISABLED_LOGGED
    if not _DISABLED_LOGGED:
        print("[Subtitles] Desativado via ENABLE_SUBTITLES=false")
        _DISABLED_LOGGED = True


def _output_folder(subject):
    platform = subject.get("_output_platform")
    return content_output_dir(subject, platform=platform)


def _resolve_timing_offset(cenas_data, platform: str = "youtube_dark") -> float:
    """Desloca legendas para coincidir com intro visual no render."""

    if not should_show_intro(platform):
        return 0.0

    return get_render_style(platform).intro_seconds


def _resolve_audio_duration(cenas_data, product=None) -> float | None:
    """Resolve duração real do áudio via ffprobe (nunca estimativa)."""

    folder = _output_folder(product) if product else None
    audio_candidates: list[Path] = []

    if folder:
        audio_candidates.append(folder / "assets" / "audio" / "narracao.mp3")

    if isinstance(cenas_data, dict):
        audio_path = cenas_data.get("audio_path")
        if audio_path:
            audio_candidates.append(Path(audio_path))

    for audio in audio_candidates:
        if audio.exists():
            probed = probe_duration(str(audio))
            if probed > 0:
                print(f"  🎧 Legendas: duração real do MP3 (ffprobe) = {probed:.2f}s")
                return probed

    if isinstance(cenas_data, dict):
        duration = cenas_data.get("audio_duration")
        if duration:
            return float(duration)

    return None


def generate_subtitles(result):
    """Gera legendas documentais via Subtitle Engine."""

    if not subtitles_enabled():
        log_subtitles_disabled_once()
        return None

    product = result["produto"]
    platform = product.get("_output_platform", result.get("platform", "youtube_dark"))
    folder = _output_folder(product)
    folder.mkdir(parents=True, exist_ok=True)

    cenas_data = result.get("cenas", {})

    if isinstance(cenas_data, dict):
        scenes = cenas_data.get("cenas", [])
    else:
        scenes = cenas_data

    if not scenes:
        texto = result.get("conteudo", {}).get("texto_narracao", "")
        if texto:
            scenes = [{"tempo": "0-30", "narracao": texto}]

    timing_offset = _resolve_timing_offset(cenas_data, platform)
    audio_duration = _resolve_audio_duration(cenas_data, product)

    subtitle_file = write_subtitles(
        scenes,
        folder,
        basename="captions",
        platform=platform,
        timing_offset=timing_offset,
        audio_duration=audio_duration,
    )

    if subtitle_file is None:
        return None

    print(f"📝 Legenda criada: {subtitle_file.resolve()}")

    return subtitle_file.resolve()


def get_subtitle_ffmpeg_filter(subtitle_path: Path, platform: str = "youtube_dark") -> str:
    """Retorna filtro FFmpeg para legendas (prefere ASS se disponível)."""

    if not subtitles_enabled():
        return ""

    ass_path = subtitle_path.with_suffix(".ass")
    if ass_path.exists():
        return ffmpeg_subtitle_filter(ass_path, platform)

    return ffmpeg_subtitle_filter(subtitle_path, platform)
