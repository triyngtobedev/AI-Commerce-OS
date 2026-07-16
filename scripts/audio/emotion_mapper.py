"""
Mapeamento centralizado de emoções para SSML e efeitos visuais.

Evita ifs espalhados — toda interpretação emocional passa por aqui.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EmotionProfile:
    """Perfil SSML e prosódia para uma emoção."""

    azure_style: str
    rate: str
    pitch: str
    break_before: str
    break_after: str
    emphasis_level: str
    scene_motion: str
    transition_speed: str
    zoom_intensity: float
    contrast_boost: float


EMOTION_PROFILES: dict[str, EmotionProfile] = {
    "mystery": EmotionProfile(
        azure_style="serious",
        rate="-6%",
        pitch="-3Hz",
        break_before="400ms",
        break_after="600ms",
        emphasis_level="moderate",
        scene_motion="zoom_in_center",
        transition_speed="slow",
        zoom_intensity=0.08,
        contrast_boost=1.05,
    ),
    "impact": EmotionProfile(
        azure_style="excited",
        rate="+2%",
        pitch="+2Hz",
        break_before="200ms",
        break_after="300ms",
        emphasis_level="strong",
        scene_motion="zoom_in_center",
        transition_speed="fast",
        zoom_intensity=0.18,
        contrast_boost=1.15,
    ),
    "sad": EmotionProfile(
        azure_style="sad",
        rate="-8%",
        pitch="-5Hz",
        break_before="500ms",
        break_after="700ms",
        emphasis_level="reduced",
        scene_motion="zoom_out_center",
        transition_speed="slow",
        zoom_intensity=0.05,
        contrast_boost=0.95,
    ),
    "calm": EmotionProfile(
        azure_style="calm",
        rate="-3%",
        pitch="-1Hz",
        break_before="300ms",
        break_after="400ms",
        emphasis_level="moderate",
        scene_motion="pan_right",
        transition_speed="normal",
        zoom_intensity=0.06,
        contrast_boost=1.0,
    ),
    "warning": EmotionProfile(
        azure_style="fearful",
        rate="+1%",
        pitch="+1Hz",
        break_before="300ms",
        break_after="500ms",
        emphasis_level="strong",
        scene_motion="pan_left",
        transition_speed="fast",
        zoom_intensity=0.12,
        contrast_boost=1.2,
    ),
    "neutral": EmotionProfile(
        azure_style="general",
        rate="-2%",
        pitch="+0Hz",
        break_before="400ms",
        break_after="400ms",
        emphasis_level="moderate",
        scene_motion="pan_left",
        transition_speed="normal",
        zoom_intensity=0.08,
        contrast_boost=1.05,
    ),
}

DEFAULT_EMOTION = "calm"


class EmotionMapper:
    """Interpretador emocional centralizado para SSML e Scene Engine."""

    def __init__(self, profiles: Optional[dict[str, EmotionProfile]] = None):
        self.profiles = profiles or EMOTION_PROFILES

    def resolve(self, emotion: str) -> EmotionProfile:
        key = (emotion or DEFAULT_EMOTION).lower().strip()
        return self.profiles.get(key, self.profiles[DEFAULT_EMOTION])

    def azure_express_as(self, emotion: str) -> str:
        return self.resolve(emotion).azure_style

    def rate_for(self, emotion: str, intensity: float = 0.5) -> str:
        profile = self.resolve(emotion)
        base = profile.rate
        if intensity > 0.7 and emotion == "impact":
            return "+4%"
        if intensity < 0.3 and emotion in ("mystery", "calm", "sad"):
            return "-10%"
        return base

    def pitch_for(self, emotion: str, intensity: float = 0.5) -> str:
        profile = self.resolve(emotion)
        if intensity > 0.8:
            adjustment = "+2Hz" if "+" in profile.pitch else profile.pitch
            return adjustment
        return profile.pitch

    def break_before(self, emotion: str) -> str:
        return self.resolve(emotion).break_before

    def break_after(self, emotion: str) -> str:
        return self.resolve(emotion).break_after

    def emphasis_level(self, emotion: str) -> str:
        return self.resolve(emotion).emphasis_level

    def scene_motion(self, emotion: str) -> str:
        return self.resolve(emotion).scene_motion

    def transition_speed(self, emotion: str) -> str:
        return self.resolve(emotion).transition_speed

    def zoom_intensity(self, emotion: str, intensity: float = 0.5) -> float:
        base = self.resolve(emotion).zoom_intensity
        return base * (0.5 + intensity)

    def contrast_boost(self, emotion: str) -> float:
        return self.resolve(emotion).contrast_boost


_default_mapper: Optional[EmotionMapper] = None


def get_emotion_mapper() -> EmotionMapper:
    global _default_mapper
    if _default_mapper is None:
        _default_mapper = EmotionMapper()
    return _default_mapper
