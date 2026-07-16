"""
Subtitle Engine — legendas documentais profissionais.

Gera SRT otimizado para YouTube com:
  - blocos curtos (máx. 2 linhas)
  - área segura inferior
  - timing proporcional por palavra dentro dos timestamps do áudio
  - destaque em palavras-chave via ASS (quando suportado)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from scripts.core.brand_engine import get_subtitle_style


def _format_srt_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds % 1) * 1000))

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _parse_srt_time(value: str) -> float:
    """Converte timestamp SRT (HH:MM:SS,mmm) para segundos."""

    hours, minutes, rest = value.strip().split(":")
    secs, millis = rest.split(",")
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(secs)
        + int(millis) / 1000.0
    )


def _split_into_lines(text: str, max_chars: int = 38, max_lines: int = 2) -> str:
    """Divide texto em no máximo 2 linhas curtas."""

    text = text.strip()
    if not text:
        return ""

    if len(text) <= max_chars:
        return text

    words = text.split()
    lines = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip() if current else word

        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

            if len(lines) >= max_lines:
                break

    if current and len(lines) < max_lines:
        lines.append(current)

    if len(lines) > max_lines:
        lines = lines[:max_lines]

    return "\n".join(lines)


def _chunk_by_words(
    text: str,
    max_words: int = 8,
    max_chars: int = 76,
) -> list[str]:
    """
    Divide narração em blocos de legenda por palavras.
    Prioriza quebras em pontuação forte.
    """

    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []

    sentences = re.split(r"(?<=[.!?…])\s+", text)
    chunks = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        words = sentence.split()

        for i in range(0, len(words), max_words):
            block = " ".join(words[i : i + max_words])
            candidate = f"{current} {block}".strip() if current else block

            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(_split_into_lines(current))
                current = block

        if current and current.rstrip()[-1:] in ".!?…":
            chunks.append(_split_into_lines(current))
            current = ""

    if current:
        chunks.append(_split_into_lines(current))

    return [c for c in chunks if c]


def _emphasize_keywords(text: str, keywords: Optional[list[str]] = None) -> str:
    """Destaca palavras importantes (para ASS). Mantém texto limpo no SRT."""

    if not keywords:
        return text

    result = text
    for word in keywords:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        result = pattern.sub(f"{{\\b1}}{word}{{\\b0}}", result)

    return result


def _extract_keywords(text: str, limit: int = 2) -> list[str]:
    """Extrai palavras longas/numéricas para destaque."""

    candidates = re.findall(r"\b\d{4}\b|\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]{4,}\b", text)
    return candidates[:limit]


def _scene_bounds(scene: dict) -> tuple[float, float]:
    """Resolve início/fim da cena a partir dos timestamps sincronizados."""

    inicio = scene.get("tempo_inicio")
    fim = scene.get("tempo_fim")

    if inicio is not None and fim is not None:
        return float(inicio), float(fim)

    tempo = scene.get("tempo", "0-5")
    try:
        start, end = tempo.split("-")
        return float(start), float(end)
    except ValueError:
        duration = scene.get("duration_seconds")
        if duration:
            return 0.0, float(duration)
        return 0.0, 5.0


def validate_srt_timing(
    srt_content: str,
    audio_duration: float,
    *,
    timing_offset: float = 0.0,
    tolerance: float = 1.5,
) -> tuple[bool, str]:
    """
    Valida se o SRT cobre a duração do áudio final.
    Retorna (ok, motivo).
    """

    if not srt_content.strip():
        return False, "SRT vazio"

    if audio_duration <= 0:
        return True, "sem áudio para validar"

    timestamps = re.findall(
        r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})",
        srt_content,
    )
    if not timestamps:
        return False, "nenhum bloco de legenda encontrado"

    last_end = _parse_srt_time(timestamps[-1][1])
    expected_end = audio_duration + timing_offset
    delta = abs(last_end - expected_end)

    if last_end > expected_end + tolerance:
        return False, (
            f"legendas ultrapassam áudio ({last_end:.1f}s > {expected_end:.1f}s)"
        )

    if last_end < expected_end - tolerance * 2:
        return False, (
            f"legendas terminam cedo demais ({last_end:.1f}s vs {expected_end:.1f}s)"
        )

    return True, "ok"


def generate_scene_subtitles(
    scenes: list,
    style: Optional[dict] = None,
    *,
    timing_offset: float = 0.0,
    audio_duration: Optional[float] = None,
) -> tuple[str, str]:
    """
    Gera conteúdo SRT e ASS a partir de cenas sincronizadas.
    timing_offset desloca legendas para alinhar com intro visual do render.
    Retorna (srt_content, ass_content).
    """

    style = style or get_subtitle_style()
    max_words = style.get("max_words_per_block", 6)
    max_chars = style.get("max_chars", 64)
    offset = max(0.0, float(timing_offset))

    srt_lines = []
    ass_events = []
    index = 1

    for scene in scenes:
        inicio, fim = _scene_bounds(scene)

        texto = scene.get("narracao", scene.get("texto", ""))
        if not texto:
            continue

        chunks = _chunk_by_words(texto, max_words=max_words, max_chars=max_chars)
        if not chunks:
            continue

        duration = max(0.8, fim - inicio)
        word_counts = [max(1, len(c.replace("\n", " ").split())) for c in chunks]
        total_words = sum(word_counts) or 1
        current = float(inicio) + offset
        scene_end = float(fim) + offset

        for chunk, word_count in zip(chunks, word_counts):
            chunk_duration = max(0.35, (word_count / total_words) * duration)
            chunk_end = min(current + chunk_duration, scene_end)

            if chunk_end <= current:
                continue

            srt_lines.append(f"{index}")
            srt_lines.append(
                f"{_format_srt_time(current)} --> {_format_srt_time(chunk_end)}"
            )
            srt_lines.append(chunk)
            srt_lines.append("")

            keywords = _extract_keywords(chunk)
            ass_text = _emphasize_keywords(chunk.replace("\n", "\\N"), keywords)
            ass_events.append(
                f"Dialogue: 0,{_format_ass_time(current)},"
                f"{_format_ass_time(chunk_end)},Default,,0,0,0,,{ass_text}"
            )

            index += 1
            current = chunk_end

    srt_content = "\n".join(srt_lines)
    ass_content = _build_ass_header(style) + "\n".join(ass_events)

    if audio_duration and audio_duration > 0:
        ok, reason = validate_srt_timing(
            srt_content,
            audio_duration,
            timing_offset=offset,
        )
        if not ok:
            print(f"  ⚠️ Validação SRT: {reason}")

    return srt_content, ass_content


def _format_ass_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds % 1) * 100))
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def _build_ass_header(style: dict) -> str:
    font = style.get("font_name", "Arial")
    size = style.get("font_size", 44)
    margin_v = style.get("margin_v", 92)
    outline = style.get("outline", 3)

    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,{outline},2,2,60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def write_subtitles(
    scenes: list,
    output_dir: Path,
    basename: str = "captions",
    *,
    platform: str = "youtube_dark",
    timing_offset: float = 0.0,
    audio_duration: Optional[float] = None,
) -> Path:
    """Escreve SRT e ASS no diretório de saída. Retorna path do SRT."""

    output_dir.mkdir(parents=True, exist_ok=True)
    style = get_subtitle_style(platform)
    srt_content, ass_content = generate_scene_subtitles(
        scenes,
        style=style,
        timing_offset=timing_offset,
        audio_duration=audio_duration,
    )

    srt_path = output_dir / f"{basename}.srt"
    ass_path = output_dir / f"{basename}.ass"

    srt_path.write_text(srt_content, encoding="utf-8")
    ass_path.write_text(ass_content, encoding="utf-8")

    return srt_path


def ffmpeg_subtitle_filter(subtitle_path: Path, platform: str = "youtube_dark") -> str:
    """Retorna filtro FFmpeg para legendas com estilo documental."""

    style = get_subtitle_style(platform)
    path = subtitle_path.resolve().as_posix().replace(":", "\\:")

    if subtitle_path.suffix.lower() == ".ass":
        return f"ass='{path}'"

    force_style = (
        f"FontName={style['font_name']},"
        f"FontSize={style['font_size']},"
        f"PrimaryColour=&HFFFFFF,"
        f"OutlineColour=&H000000,"
        f"Outline={style['outline']},"
        f"Shadow={style.get('shadow', 2)},"
        f"MarginV={style['margin_v']},"
        f"Alignment=2"
    )

    return f"subtitles='{path}':force_style='{force_style}'"
