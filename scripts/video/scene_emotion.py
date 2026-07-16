"""
Integração da Emotional Timeline com Scene Engine.

Cada cena recebe emotion, intensity, visual_intent e referência à timeline.
"""

from __future__ import annotations

from typing import Any, Optional

from scripts.audio.emotion_mapper import get_emotion_mapper
from scripts.core.emotional_timeline import EmotionalTimeline, TimelineSection
from scripts.core.visual_intent_engine import resolve_visual_intent


def apply_timeline_to_scenes(
    scenes_data: dict | list,
    timeline: EmotionalTimeline,
) -> dict:
    """
    Enriquece cenas com dados emocionais e visuais da timeline compartilhada.
    Nunca recalcula emoções — consome apenas a timeline.
    """

    if isinstance(scenes_data, dict):
        result = dict(scenes_data)
        scenes = list(result.get("cenas", []))
    else:
        result = {"cenas": list(scenes_data or [])}
        scenes = result["cenas"]

    timeline_sections = timeline.sections
    mapper = get_emotion_mapper()

    for index, scene in enumerate(scenes):
        section = _match_timeline_section(index, timeline_sections, scene)
        if not section:
            continue

        visual_spec = resolve_visual_intent(section)

        scene["emotion"] = section.emotion
        scene["intensity"] = section.intensity
        scene["visual_intent"] = section.visual_intent
        scene["camera_motion"] = section.camera_motion
        scene["timeline"] = section.to_dict()
        scene["visual_spec"] = visual_spec.to_dict()
        scene["scene_motion"] = visual_spec.camera or mapper.scene_motion(section.emotion)
        scene["transition_hint"] = section.transition_hint
        scene["transition_speed"] = mapper.transition_speed(section.emotion)
        scene["zoom_intensity"] = mapper.zoom_intensity(
            section.emotion, section.intensity
        )
        scene["contrast_boost"] = mapper.contrast_boost(section.emotion)

        duration = section.real_duration or section.duration
        if duration > 0:
            scene["duration_hint"] = duration
            scene["duration_seconds"] = duration
            scene["tempo_inicio"] = section.start_time
            scene["tempo_fim"] = round(section.start_time + duration, 2)

        if section.start_time >= 0 and duration > 0:
            scene["tempo"] = f"{int(section.start_time)}-{int(section.start_time + duration)}"

    result["cenas"] = scenes
    result["emotional_timeline"] = timeline.to_dict()
    return result


def _match_timeline_section(
    scene_index: int,
    sections: list[TimelineSection],
    scene: dict,
) -> Optional[TimelineSection]:
    scene_type = scene.get("tipo", "")

    for section in sections:
        if section.section_key and section.section_key == scene_type:
            return section

    if scene_index < len(sections):
        return sections[scene_index]

    return None


def get_scene_render_hints(scene: dict) -> dict[str, Any]:
    """
    Retorna hints de renderização baseados na emoção e visual intent da cena.
    Arquitetura preparada para efeitos futuros (zoom, shake, flash, etc.).
    """

    emotion = scene.get("emotion", "calm")
    intensity = float(scene.get("intensity", 0.5))
    mapper = get_emotion_mapper()
    visual_spec = scene.get("visual_spec", {})
    effect_hints = scene.get("effect_hints", {})

    return {
        "motion": scene.get("scene_motion") or visual_spec.get("camera") or mapper.scene_motion(emotion),
        "camera_motion": scene.get("camera_motion", "slow_push"),
        "visual_intent": scene.get("visual_intent", "general_narrative"),
        "color_palette": visual_spec.get("color_palette", "neutral"),
        "transition_hint": scene.get("transition_hint", "crossfade"),
        "transition_speed": scene.get("transition_speed") or mapper.transition_speed(emotion),
        "zoom_intensity": scene.get("zoom_intensity") or mapper.zoom_intensity(emotion, intensity),
        "contrast_boost": scene.get("contrast_boost") or mapper.contrast_boost(emotion),
        "quality_score": scene.get("quality_score", 0.0),
        "silence_before": scene.get("timeline", {}).get("pause_before", 0.0),
        "silence_after": scene.get("timeline", {}).get("pause_after", 0.0),
        "effects": effect_hints.get("effects", []),
        "flash_enabled": effect_hints.get("flash_enabled", False),
        "shake_enabled": effect_hints.get("shake_enabled", False),
        "blur_enabled": effect_hints.get("blur_enabled", False),
        "soundtrack_hint": effect_hints.get("soundtrack_hint", "neutral_bed"),
    }
