"""
Emotional Timeline — fonte única de verdade emocional para toda a pipeline.

Fluxo:
    Script → Director Engine → EmotionalTimeline → Narration → sync → Scene → Renderer

Nunca recalcular emoções em módulos diferentes.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from scripts.audio.emotion_mapper import get_emotion_mapper
from scripts.creative.script_parser import parse_script_sections

DEFAULT_SCENE_WEIGHTS: dict[str, float] = {
    "hook": 6.0,
    "contexto": 12.0,
    "desenvolvimento": 18.0,
    "desenvolvimento_1": 18.0,
    "desenvolvimento_2": 18.0,
    "revelacao": 18.0,
    "consequencias": 12.0,
    "impacto": 12.0,
    "encerramento": 6.0,
    "problema": 10.0,
    "teste": 12.0,
    "resultado": 14.0,
    "cta": 6.0,
    "gancho": 6.0,
    "roteiro": 20.0,
}

DEFAULT_TRANSITION_BY_EMOTION: dict[str, str] = {
    "mystery": "fade_slow",
    "impact": "cut_fast",
    "calm": "crossfade",
    "warning": "flash_cut",
    "sad": "fade_slow",
    "neutral": "crossfade",
}

DEFAULT_WEIGHT = 10.0
WORDS_PER_SECOND = 2.5


@dataclass
class TimelineSection:
    text: str
    emotion: str
    intensity: float
    start_time: float = 0.0
    pause_before: float = 0.0
    pause_after: float = 0.0
    scene_weight: float = DEFAULT_WEIGHT
    section_key: str = ""
    duration: float = 0.0
    visual_intent: str = "general_narrative"
    camera_motion: str = "slow_push"
    estimated_duration: float = 0.0
    real_duration: float = 0.0
    transition_hint: str = "crossfade"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EmotionalTimeline:
    """Timeline emocional compartilhada por Script, Scene, SSML e Renderer."""

    sections: list[TimelineSection] = field(default_factory=list)
    total_duration: float = 0.0
    director_meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sections": [s.to_dict() for s in self.sections],
            "total_duration": self.total_duration,
            "director_meta": self.director_meta,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EmotionalTimeline":
        sections = [
            TimelineSection(**item)
            for item in data.get("sections", [])
        ]
        return cls(
            sections=sections,
            total_duration=float(data.get("total_duration", 0.0)),
            director_meta=data.get("director_meta", {}),
        )

    @classmethod
    def from_script(
        cls,
        script: dict,
        audio_duration: Optional[float] = None,
        director_meta: Optional[dict] = None,
    ) -> "EmotionalTimeline":
        """Constrói timeline a partir do roteiro parseado."""

        parsed = parse_script_sections(script)
        mapper = get_emotion_mapper()
        sections: list[TimelineSection] = []

        for item in parsed.get("sections", []):
            emotion = item.get("emotion", "calm")
            intensity = float(item.get("intensity", 0.5))
            profile = mapper.resolve(emotion)
            section_key = item.get("section_key", "")

            pause_before = float(item.get("pause_before", 0.0))
            pause_after = float(item.get("pause_after", 0.0))

            if pause_before == 0.0:
                pause_before = _ms_to_seconds(profile.break_before)
            if pause_after == 0.0:
                pause_after = _ms_to_seconds(profile.break_after)

            weight = DEFAULT_SCENE_WEIGHTS.get(section_key, DEFAULT_WEIGHT)
            word_count = max(1, len(item["text"].split()))
            estimated = round(word_count / WORDS_PER_SECOND, 2)

            sections.append(TimelineSection(
                text=item["text"],
                emotion=emotion,
                intensity=intensity,
                pause_before=pause_before,
                pause_after=pause_after,
                scene_weight=weight,
                section_key=section_key,
                visual_intent=item.get("visual_intent", "general_narrative"),
                camera_motion=item.get("camera_motion", profile.scene_motion),
                estimated_duration=estimated,
                transition_hint=DEFAULT_TRANSITION_BY_EMOTION.get(emotion, "crossfade"),
            ))

        timeline = cls(
            sections=sections,
            director_meta=director_meta or script.get("_director", {}),
        )
        timeline._compute_timings(audio_duration)
        return timeline

    def _compute_timings(self, audio_duration: Optional[float] = None) -> None:
        """Calcula start_time e duration por seção."""

        if not self.sections:
            self.total_duration = 0.0
            return

        if audio_duration and audio_duration > 0:
            self._scale_to_audio(audio_duration)
            return

        current = 0.0
        for section in self.sections:
            section.start_time = round(current + section.pause_before, 2)
            if section.estimated_duration <= 0:
                word_count = max(1, len(section.text.split()))
                section.estimated_duration = round(word_count / WORDS_PER_SECOND, 2)
            section.duration = section.estimated_duration
            section.real_duration = 0.0
            current = section.start_time + section.duration + section.pause_after

        self.total_duration = round(current, 2)

    def _scale_to_audio(self, audio_duration: float) -> None:
        """Escala durações proporcionalmente ao áudio real."""

        estimates = []
        for section in self.sections:
            if section.estimated_duration <= 0:
                word_count = max(1, len(section.text.split()))
                section.estimated_duration = round(word_count / WORDS_PER_SECOND, 2)
            estimates.append(
                section.estimated_duration + section.pause_before + section.pause_after
            )

        total_estimate = sum(estimates) or 1.0
        current = 0.0

        for index, section in enumerate(self.sections):
            ratio = estimates[index] / total_estimate
            raw_duration = max(1.0, round(ratio * audio_duration, 2))

            section.start_time = round(current, 2)
            section.real_duration = raw_duration
            section.duration = raw_duration
            current = round(current + raw_duration, 2)

        if self.sections:
            delta = round(audio_duration - current, 2)
            if abs(delta) >= 0.01:
                last = self.sections[-1]
                last.real_duration = max(1.0, round(last.real_duration + delta, 2))
                last.duration = last.real_duration
                current = audio_duration

        self.total_duration = round(audio_duration, 2)


def build_emotional_timeline(
    script: dict,
    audio_duration: Optional[float] = None,
    director_meta: Optional[dict] = None,
) -> EmotionalTimeline:
    """Ponto de entrada — produz timeline após Script Generator / Director."""

    return EmotionalTimeline.from_script(
        script,
        audio_duration=audio_duration,
        director_meta=director_meta,
    )


def _ms_to_seconds(break_ms: str) -> float:
    value = break_ms.replace("ms", "").replace("s", "").strip()
    try:
        if "ms" in break_ms or float(value) > 10:
            return float(value) / 1000.0
        return float(value)
    except ValueError:
        return 0.4
