"""
Pontos de integração para efeitos emocionais guiados pela Emotional Timeline.

Não implementa efeitos complexos — apenas expõe hints para Scene/Render Engine.
"""

from __future__ import annotations

from typing import Any

from scripts.core.emotional_timeline import EmotionalTimeline, TimelineSection

EFFECTS_BY_EMOTION: dict[str, list[str]] = {
    "mystery": ["fade", "slow_zoom"],
    "impact": ["flash", "zoom", "shake"],
    "calm": ["fade", "slow_pan"],
    "warning": ["shake", "contrast_boost"],
    "sad": ["fade", "blur_light"],
    "neutral": ["crossfade"],
}

EFFECTS_BY_TRANSITION: dict[str, list[str]] = {
    "fade_slow": ["fade"],
    "cut_fast": ["flash"],
    "crossfade": ["fade"],
    "flash_cut": ["flash"],
}


def get_section_effect_hints(section: TimelineSection | dict) -> dict[str, Any]:
    """
    Retorna hints de efeitos para uma seção da timeline.
    Consumido exclusivamente pela Scene/Render Engine.
    """

    if isinstance(section, TimelineSection):
        emotion = section.emotion
        intensity = section.intensity
        transition = section.transition_hint
        pause_before = section.pause_before
        pause_after = section.pause_after
        camera = section.camera_motion
    else:
        emotion = section.get("emotion", "calm")
        intensity = float(section.get("intensity", 0.5))
        transition = section.get("transition_hint", "crossfade")
        pause_before = float(section.get("pause_before", 0.0))
        pause_after = float(section.get("pause_after", 0.0))
        camera = section.get("camera_motion", "slow_push")

    effects = list(EFFECTS_BY_EMOTION.get(emotion, ["crossfade"]))
    effects.extend(EFFECTS_BY_TRANSITION.get(transition, []))

    if pause_before >= 0.5:
        effects.append("dramatic_silence")

    if intensity > 0.8:
        effects.append("zoom")

    return {
        "effects": list(dict.fromkeys(effects)),
        "zoom_intensity": min(0.25, 0.08 + intensity * 0.15),
        "flash_enabled": "flash" in effects and intensity > 0.7,
        "blur_enabled": "blur_light" in effects,
        "shake_enabled": "shake" in effects and intensity > 0.6,
        "fade_in": transition in ("fade_slow", "crossfade"),
        "fade_out": transition in ("fade_slow", "crossfade"),
        "dramatic_silence_before": pause_before,
        "dramatic_silence_after": pause_after,
        "camera_motion": camera,
        "soundtrack_hint": _soundtrack_hint(emotion, intensity),
    }


def _soundtrack_hint(emotion: str, intensity: float) -> str:
    if emotion == "mystery" and intensity < 0.5:
        return "ambient_tension_low"
    if emotion == "impact" and intensity > 0.7:
        return "dramatic_stinger"
    if emotion == "calm":
        return "ambient_soft"
    if emotion == "warning":
        return "tension_rising"
    return "neutral_bed"


def apply_effect_hints_to_scenes(
    scenes_data: dict,
    timeline: EmotionalTimeline,
) -> dict:
    """Anexa hints de efeitos emocionais às cenas via timeline."""

    result = dict(scenes_data)
    scenes = list(result.get("cenas", []))
    sections = timeline.sections

    for index, scene in enumerate(scenes):
        section = sections[index] if index < len(sections) else None
        if section:
            scene["effect_hints"] = get_section_effect_hints(section)

    result["cenas"] = scenes
    return result
