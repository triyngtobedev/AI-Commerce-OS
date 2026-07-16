"""
Construtor de SSML emocional para Azure Speech SDK.

Utiliza exclusivamente EmotionMapper para interpretação emocional.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Union

from scripts.audio.emotion_mapper import get_emotion_mapper
from scripts.audio.narration_models import NarrationSection
from scripts.audio.tts_text_prep import prepare_text_for_tts
from scripts.core.emotional_timeline import TimelineSection

YOUTUBE_SECTIONS = [
    "hook",
    "contexto",
    "desenvolvimento",
    "revelacao",
    "consequencias",
    "encerramento",
]

TIKTOK_SECTIONS = [
    "hook",
    "problema",
    "teste",
    "resultado",
    "cta",
]

SECTION_PROSODY: Dict[str, Dict[str, str]] = {
    "hook": {"rate": "+2%", "pitch": "+1Hz"},
    "contexto": {"rate": "-2%", "pitch": "-1Hz"},
    "desenvolvimento": {"rate": "-4%", "pitch": "-2Hz"},
    "revelacao": {"rate": "-8%", "pitch": "-4Hz"},
    "consequencias": {"rate": "-5%", "pitch": "-2Hz"},
    "encerramento": {"rate": "+1%", "pitch": "+0Hz"},
    "problema": {"rate": "-2%", "pitch": "-1Hz"},
    "teste": {"rate": "-3%", "pitch": "-1Hz"},
    "resultado": {"rate": "-6%", "pitch": "-3Hz"},
    "cta": {"rate": "+3%", "pitch": "+2Hz"},
}

EMPHASIS_SECTIONS = {"hook", "revelacao"}

_NUMBER_PATTERN = re.compile(r"\b(\d{1,3}(?:\.\d{3})+|\d+)\b")
_DATE_PATTERN = re.compile(
    r"\b(\d{1,2}/\d{2}/\d{4}|\d{1,2}\s+de\s+\w+\s+de\s+\d{4})\b",
    re.IGNORECASE,
)
_EXCLAMATION_PATTERN = re.compile(r"([^!]*!+)")


def escape_ssml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _merge_prosody(base_rate: str, base_pitch: str, section_key: str) -> tuple[str, str]:
    section = SECTION_PROSODY.get(section_key, {})
    rate = section.get("rate", base_rate)
    pitch = section.get("pitch", base_pitch)
    return rate, pitch


def _emphasize_numbers_and_dates(text: str, level: str = "moderate") -> str:
    def _wrap(match: re.Match) -> str:
        return f'<emphasis level="{level}">{match.group(0)}</emphasis>'

    text = _DATE_PATTERN.sub(_wrap, text)
    text = _NUMBER_PATTERN.sub(_wrap, text)
    return text


def _emphasize_exclamations(text: str, level: str = "strong") -> str:
    def _wrap(match: re.Match) -> str:
        return f'<emphasis level="{level}">{match.group(0)}</emphasis>'

    return _EXCLAMATION_PATTERN.sub(_wrap, text)


def _emphasize_first_sentence(text: str, level: str = "moderate") -> str:
    stripped = text.strip()
    if not stripped:
        return text

    match = re.match(r"^(.+?[.!?])(\s+.*)?$", stripped, re.DOTALL)
    if not match:
        return f'<emphasis level="{level}">{stripped}</emphasis>'

    first = match.group(1)
    rest = match.group(2) or ""
    return f'<emphasis level="{level}">{first}</emphasis>{rest}'


def _prepare_section_text(
    section_key: str,
    raw_text: str,
    emotion: str = "calm",
    intensity: float = 0.5,
) -> str:
    mapper = get_emotion_mapper()
    prepared = prepare_text_for_tts(raw_text)
    escaped = escape_ssml(prepared)
    emphasis = mapper.emphasis_level(emotion)

    escaped = _emphasize_numbers_and_dates(escaped, emphasis)
    escaped = _emphasize_exclamations(escaped, emphasis)

    if section_key in EMPHASIS_SECTIONS or intensity > 0.7:
        escaped = _emphasize_first_sentence(escaped, emphasis)

    return escaped


def _emotion_ssml_block(
    content: str,
    emotion: str,
    rate: str,
    pitch: str,
    intensity: float,
) -> str:
    """Envolve conteúdo com express-as emocional + prosody."""

    mapper = get_emotion_mapper()
    style = mapper.azure_express_as(emotion)
    emotion_rate = mapper.rate_for(emotion, intensity)
    emotion_pitch = mapper.pitch_for(emotion, intensity)

    final_rate = emotion_rate or rate
    final_pitch = emotion_pitch or pitch

    return (
        f'<mstts:express-as style="{style}">'
        f'<prosody rate="{final_rate}" pitch="{final_pitch}">{content}</prosody>'
        f"</mstts:express-as>"
    )


def build_ssml_from_sections(
    sections: List[Union[NarrationSection, dict]],
    voice: str,
    base_rate: str,
    base_pitch: str,
) -> str:
    """
    Monta SSML a partir de seções emocionais (NarrationSection ou dict).
    Utiliza exclusivamente EmotionMapper.
    """

    mapper = get_emotion_mapper()
    body_parts: list[str] = []

    for index, raw_section in enumerate(sections):
        if isinstance(raw_section, (NarrationSection, TimelineSection)):
            text = raw_section.text
            emotion = raw_section.emotion
            intensity = raw_section.intensity
            section_key = raw_section.section_key
            pause_before = raw_section.pause_before
            pause_after = raw_section.pause_after
        else:
            text = (raw_section.get("text") or "").strip()
            emotion = raw_section.get("emotion", "calm")
            intensity = float(raw_section.get("intensity", 0.5))
            section_key = raw_section.get("section_key", "")
            pause_before = float(raw_section.get("pause_before", 0.0))
            pause_after = float(raw_section.get("pause_after", 0.0))

        if not text:
            continue

        rate, pitch = _merge_prosody(base_rate, base_pitch, section_key)
        content = _prepare_section_text(section_key, text, emotion, intensity)

        if pause_before > 0:
            body_parts.append(f'<break time="{int(pause_before * 1000)}ms"/>')
        elif index > 0:
            body_parts.append(f'<break time="{mapper.break_before(emotion)}"/>')

        body_parts.append(_emotion_ssml_block(content, emotion, rate, pitch, intensity))

        if index < len(sections) - 1:
            if pause_after > 0:
                body_parts.append(f'<break time="{int(pause_after * 1000)}ms"/>')
            else:
                body_parts.append(f'<break time="{mapper.break_after(emotion)}"/>')

    if not body_parts:
        return ""

    inner = "\n    ".join(body_parts)

    return (
        f'<speak version="1.0" '
        f'xmlns="http://www.w3.org/2001/10/synthesis" '
        f'xmlns:mstts="https://www.w3.org/2001/mstts" '
        f'xml:lang="pt-BR">\n'
        f'  <voice name="{voice}">\n'
        f"    {inner}\n"
        f"  </voice>\n"
        f"</speak>"
    )


def _detect_sections(script: dict) -> list[str]:
    if any(key in script for key in YOUTUBE_SECTIONS):
        return YOUTUBE_SECTIONS
    if any(key in script for key in TIKTOK_SECTIONS):
        return TIKTOK_SECTIONS
    return list(script.keys())


def build_ssml(
    script: dict,
    voice: str,
    base_rate: str,
    base_pitch: str,
) -> str:
    """
    Monta SSML completo a partir das seções do roteiro (compatibilidade retroativa).
    Delega para build_ssml_from_sections após parse emocional.
    """

    from scripts.creative.script_parser import parse_script_sections

    parsed = parse_script_sections(script)
    sections = parsed.get("sections", [])

    if not sections:
        return ""

    return build_ssml_from_sections(sections, voice, base_rate, base_pitch)
