"""
Sincronização da Emotional Timeline com duração real do áudio.

Fluxo:
    Narration → Áudio Final → probe_duration() → sync_timeline_to_audio() → Scene Engine
"""

from __future__ import annotations

from typing import Optional

from scripts.core.emotional_timeline import EmotionalTimeline
from scripts.video.media_probe import probe_duration

WORDS_PER_SECOND = 2.5


def _section_time_weights(timeline: EmotionalTimeline) -> list[float]:
    """Peso temporal de cada seção baseado em texto + pausas."""

    weights = []
    for section in timeline.sections:
        word_count = max(1, len(section.text.split()))
        speech_time = word_count / WORDS_PER_SECOND
        pause_time = section.pause_before + section.pause_after
        weights.append(speech_time + pause_time)
    return weights


def sync_timeline_to_audio(
    timeline: EmotionalTimeline,
    audio_path: str,
    fallback_duration: Optional[float] = None,
) -> EmotionalTimeline:
    """
    Atualiza timeline com duração real do áudio.
    Preenche real_duration, duration, start_time e total_duration.
    """

    audio_duration = probe_duration(audio_path)

    if audio_duration <= 0 and fallback_duration:
        audio_duration = fallback_duration

    if audio_duration <= 0 or not timeline.sections:
        return timeline

    weights = _section_time_weights(timeline)
    total_weight = sum(weights) or 1.0

    current = 0.0
    for index, section in enumerate(timeline.sections):
        ratio = weights[index] / total_weight
        real = max(0.5, round(ratio * audio_duration, 2))

        section.start_time = round(current, 2)
        section.real_duration = real
        section.duration = real
        current = round(current + real, 2)

    delta = round(audio_duration - current, 2)
    if timeline.sections and abs(delta) >= 0.01:
        last = timeline.sections[-1]
        last.real_duration = max(0.5, round(last.real_duration + delta, 2))
        last.duration = last.real_duration

    timeline.total_duration = round(audio_duration, 2)
    timeline.director_meta["synced_to_audio"] = True
    timeline.director_meta["audio_path"] = str(audio_path)

    return timeline


def estimate_section_durations(
    timeline: EmotionalTimeline,
    total_duration: float,
) -> list[float]:
    """Estima durações por seção sem áudio real (para testes/planejamento)."""

    weights = _section_time_weights(timeline)
    total_weight = sum(weights) or 1.0
    return [
        max(0.5, round((w / total_weight) * total_duration, 2))
        for w in weights
    ]
