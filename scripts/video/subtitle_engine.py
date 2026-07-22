"""
Subtitle Engine — legendas documentais profissionais.

Gera SRT otimizado para YouTube com:
  - blocos curtos (máx. 8 palavras por linha)
  - timing sincronizado com duração real do MP3 (ffprobe)
  - área segura inferior
  - texto sanitizado em português
  - destaque em palavras-chave via ASS (quando suportado)
"""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Optional

from scripts.core.brand_engine import get_subtitle_style
from scripts.video.media_probe import probe_duration

# Karaoke word-by-word (template n8n Eli Rigobeli — palavra amarela enquanto falada).
SUBTITLE_KARAOKE = os.getenv("SUBTITLE_KARAOKE", "true").lower() in {"1", "true", "yes"}
KARAOKE_HIGHLIGHT_COLOR = os.getenv("SUBTITLE_KARAOKE_COLOR", "gold")

DEFAULT_MAX_WORDS_PER_BLOCK = 8

# Remove caracteres de controle e símbolos fora do português comum.
_NON_PT_CHARS = re.compile(r"[^\w\s.,!?…:;\"'()-–—áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ0-9]", re.UNICODE)


def sanitize_subtitle_text(text: str) -> str:
    """Remove caracteres inválidos e normaliza encoding para legendas PT-BR."""

    if not text:
        return ""

    normalized = unicodedata.normalize("NFC", text)
    cleaned = _NON_PT_CHARS.sub("", normalized)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


# Cores ASS (formato &HAABBGGRR) — estilo canais dark YouTube
HIGHLIGHT_ASS_COLORS = {
    "gold": "&H0000D7FF",
    "red": "&H000000FF",
    "cyan": "&H00FFFF00",
}


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


def _split_into_lines(text: str, max_chars: int = 42, max_lines: int = 2) -> str:
    """Divide texto em no máximo 2 linhas curtas (4-5 palavras por linha)."""

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
    max_words: int = DEFAULT_MAX_WORDS_PER_BLOCK,
    max_chars: int = 64,
) -> list[str]:
    """
    Divide narração em blocos de legenda por palavras (máx. 8 palavras).
    Prioriza quebras em pontuação forte.
    """

    text = sanitize_subtitle_text(re.sub(r"\s+", " ", text.strip()))
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


def _emphasize_keywords(
    text: str,
    keywords: Optional[list[str]] = None,
    style: Optional[dict] = None,
) -> str:
    """
    Destaca palavras-chave com cor (ASS) — estilo Dark5/Top5s.
    Fallback: bold branco com outline preto quando sem keywords.
    """

    if not keywords:
        return text

    style = style or {}
    color_names = style.get("highlight_colors", ("gold", "red", "cyan"))
    result = text

    for index, word in enumerate(keywords):
        color_name = color_names[index % len(color_names)]
        ass_color = HIGHLIGHT_ASS_COLORS.get(color_name, HIGHLIGHT_ASS_COLORS["gold"])
        pattern = re.compile(re.escape(word), re.IGNORECASE)

        def _colorize(match: re.Match, color: str = ass_color) -> str:
            matched = match.group(0)
            return f"{{\\c{color}&\\b1}}{matched}{{\\r\\b0}}"

        result = pattern.sub(_colorize, result, count=1)

    return result


def _escape_ass_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _build_karaoke_ass_text(words: list[dict]) -> str:
    """
    Legenda estilo karaoke ASS padrão.

    Cada palavra recebe \\k (centésimos de segundo) ANTES dela.
    O renderer ASS usa SecondaryColour para destacar a sílaba ativa
    automaticamente — a cor de destaque é definida no style header,
    não precisa de \\c inline.
    """

    if not words:
        return ""

    parts: list[str] = []
    # O primeiro \\k da linha é ignorado pelo renderer, então inserimos
    # um \\k dummy para que a primeira palavra seja destacada corretamente
    first = True

    for item in words:
        word = _escape_ass_text((item.get("word") or "").strip())
        if not word:
            continue
        start = float(item.get("start", 0.0))
        end = float(item.get("end", start))
        duration_cs = max(1, int(round((end - start) * 100)))
        if first:
            parts.append(f"{{\\k{duration_cs}}}{word}")
            first = False
        else:
            parts.append(f"{{\\k{duration_cs}}}{word}")

    return " ".join(parts)


def _words_for_time_range(
    words: list[dict],
    start: float,
    end: float,
    *,
    tolerance: float = 0.05,
) -> list[dict]:
    """Filtra palavras cujo intervalo cai dentro do bloco de legenda."""

    return [
        word
        for word in words
        if float(word.get("start", 0.0)) >= start - tolerance
        and float(word.get("end", 0.0)) <= end + tolerance
    ]


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


def _scale_scenes_to_audio(
    scenes: list,
    audio_duration: float,
    *,
    timing_offset: float = 0.0,
) -> list[dict]:
    """
    Reescala timestamps das cenas para coincidir com duração real do MP3 (ffprobe).
    """

    if not scenes or audio_duration <= 0:
        return scenes

    scaled: list[dict] = []
    bounds: list[tuple[float, float]] = []

    for scene in scenes:
        start, end = _scene_bounds(scene)
        bounds.append((start, end))

    if not bounds:
        return scenes

    estimated_total = max(end for _, end in bounds) or 1.0
    scale = audio_duration / estimated_total

    for scene, (start, end) in zip(scenes, bounds):
        item = dict(scene)
        item["tempo_inicio"] = round(start * scale, 3)
        item["tempo_fim"] = round(end * scale, 3)
        scaled.append(item)

    if scaled:
        scaled[-1]["tempo_fim"] = round(audio_duration, 3)

    return scaled


def generate_scene_subtitles(
    scenes: list,
    style: Optional[dict] = None,
    *,
    timing_offset: float = 0.0,
    audio_duration: Optional[float] = None,
) -> tuple[str, str]:
    """
    Gera conteúdo SRT e ASS a partir de cenas sincronizadas.
    Usa duração real do áudio (ffprobe) quando disponível.
    """

    style = style or get_subtitle_style()
    max_words = style.get("max_words_per_block", DEFAULT_MAX_WORDS_PER_BLOCK)
    max_chars = style.get("max_chars", 58)
    min_chunk_gap = 0.06
    offset = max(0.0, float(timing_offset))

    if audio_duration and audio_duration > 0:
        scenes = _scale_scenes_to_audio(scenes, audio_duration, timing_offset=offset)

    srt_lines = []
    ass_events = []
    index = 1

    for scene in scenes:
        inicio, fim = _scene_bounds(scene)

        texto = sanitize_subtitle_text(scene.get("narracao", scene.get("texto", "")))
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
            chunk_duration = max(0.45, (word_count / total_words) * duration)
            chunk_end = min(current + chunk_duration, scene_end - min_chunk_gap)

            if chunk_end <= current + 0.08:
                continue

            srt_lines.append(f"{index}")
            srt_lines.append(
                f"{_format_srt_time(current)} --> {_format_srt_time(chunk_end)}"
            )
            srt_lines.append(chunk)
            srt_lines.append("")

            keywords = _extract_keywords(chunk)
            ass_text = _emphasize_keywords(
                sanitize_subtitle_text(chunk.replace("\n", "\\N")),
                keywords,
                style=style,
            )
            ass_events.append(
                f"Dialogue: 0,{_format_ass_time(current)},"
                f"{_format_ass_time(chunk_end)},Default,,0,0,0,,{ass_text}"
            )

            index += 1
            current = chunk_end + min_chunk_gap

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


def _build_chunks_from_words(
    words: list[dict],
    max_words: int,
    max_chars: int,
) -> list[tuple[str, float, float]]:
    """
    Agrupa palavras (com timestamps reais) em blocos de legenda.
    Quebra em pontuação forte ou nos limites de palavras/caracteres.
    Retorna (texto_formatado, start_real, end_real) por bloco.
    """

    chunks: list[tuple[str, float, float]] = []
    current: list[dict] = []

    for word in words:
        current.append(word)
        text = " ".join(item["word"] for item in current)
        ends_sentence = text.rstrip()[-1:] in ".!?…"

        if ends_sentence or len(current) >= max_words or len(text) >= max_chars:
            chunks.append((
                _split_into_lines(text, max_chars=max_chars),
                current[0]["start"],
                current[-1]["end"],
            ))
            current = []

    if current:
        text = " ".join(item["word"] for item in current)
        chunks.append((
            _split_into_lines(text, max_chars=max_chars),
            current[0]["start"],
            current[-1]["end"],
        ))

    return chunks


def generate_subtitles_from_words(
    words: list[dict],
    style: Optional[dict] = None,
    *,
    timing_offset: float = 0.0,
    karaoke: bool | None = None,
) -> tuple[str, str]:
    """
    Gera SRT e ASS a partir de palavras com timestamps reais (Whisper).
    Os tempos são ancorados na fala real, eliminando o atraso acumulado.
    """

    style = style or get_subtitle_style()
    max_words = style.get("max_words_per_block", DEFAULT_MAX_WORDS_PER_BLOCK)
    max_chars = style.get("max_chars", 58)
    offset = max(0.0, float(timing_offset))
    use_karaoke = SUBTITLE_KARAOKE if karaoke is None else karaoke

    srt_lines = []
    ass_events = []

    chunks = _build_chunks_from_words(words, max_words, max_chars)

    for index, (chunk, start, end) in enumerate(chunks, start=1):
        start_t = start + offset
        end_t = max(start_t + 0.3, end + offset)

        srt_lines.append(f"{index}")
        srt_lines.append(
            f"{_format_srt_time(start_t)} --> {_format_srt_time(end_t)}"
        )
        srt_lines.append(chunk)
        srt_lines.append("")

        if use_karaoke:
            chunk_words = _words_for_time_range(words, start, end)
            ass_text = _build_karaoke_ass_text(chunk_words) or sanitize_subtitle_text(
                chunk.replace("\n", "\\N")
            )
        else:
            keywords = _extract_keywords(chunk)
            ass_text = _emphasize_keywords(
                sanitize_subtitle_text(chunk.replace("\n", "\\N")),
                keywords,
                style=style,
            )
        ass_events.append(
            f"Dialogue: 0,{_format_ass_time(start_t)},"
            f"{_format_ass_time(end_t)},Default,,0,0,0,,{ass_text}"
        )

    srt_content = "\n".join(srt_lines)
    ass_content = _build_ass_header(style, karaoke=use_karaoke) + "\n".join(ass_events)
    return srt_content, ass_content


def _format_ass_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds % 1) * 100))
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def _build_ass_header(style: dict, *, karaoke: bool = False) -> str:
    font = style.get("font_name", "Arial")
    size = style.get("font_size", 54)
    margin_v = style.get("margin_v", 80)
    outline = style.get("outline", 3)
    shadow = style.get("shadow", 1)
    bold = -1 if style.get("bold", True) else 0
    # Branco para texto inativo, amarelo dourado para sílaba ativa (karaoke)
    primary = "&H00FFFFFF"
    secondary = (
        HIGHLIGHT_ASS_COLORS.get(KARAOKE_HIGHLIGHT_COLOR, HIGHLIGHT_ASS_COLORS["gold"])
        if karaoke
        else "&H0000D7FF"
    )

    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},{primary},{secondary},&H00000000,&H80000000,{bold},0,0,0,100,100,0,0,1,{outline},{shadow},2,60,60,{margin_v},1

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
) -> Path | None:
    """Escreve SRT e ASS no diretório de saída. Retorna path do SRT."""

    from scripts.video.subtitle_generator import subtitles_enabled

    if not subtitles_enabled():
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    style = get_subtitle_style(platform)

    srt_content = None
    ass_content = None

    # Preferir timestamps reais via transcrição do áudio final (Whisper local).
    audio_path = output_dir / "assets" / "audio" / "narracao.mp3"
    if audio_duration is None and audio_path.exists():
        probed = probe_duration(str(audio_path))
        if probed > 0:
            audio_duration = probed
            print(f"  🎧 Duração real do áudio (ffprobe): {audio_duration:.2f}s")

    if audio_path.exists():
        from scripts.video.whisper_aligner import transcribe_words

        words = transcribe_words(audio_path)
        if words:
            srt_content, ass_content = generate_subtitles_from_words(
                words,
                style=style,
                timing_offset=timing_offset,
            )
            if audio_duration and audio_duration > 0:
                ok, reason = validate_srt_timing(
                    srt_content,
                    audio_duration,
                    timing_offset=max(0.0, float(timing_offset)),
                )
                if not ok:
                    print(f"  ⚠️ Validação SRT (Whisper): {reason}")
            print(
                f"  🗣️ Legendas alinhadas por transcrição real: {len(words)} palavras"
            )

    # Fallback: distribuição estimada por cena (comportamento anterior).
    if srt_content is None:
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
        f"Bold=1,"
        f"MarginV={style['margin_v']},"
        f"Alignment=2"
    )

    return f"subtitles='{path}':force_style='{force_style}'"
