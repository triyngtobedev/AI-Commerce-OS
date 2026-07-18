"""
Integração da Emotional Timeline com Scene Engine.

Cada cena recebe emotion, intensity, visual_intent e referência à timeline.
"""

from __future__ import annotations

from typing import Any, Optional

from scripts.audio.emotion_mapper import get_emotion_mapper
from scripts.core.emotional_timeline import EmotionalTimeline, TimelineSection
from scripts.core.visual_intent_engine import resolve_visual_intent

# Mapeia tipos de cena (8) para chaves da timeline (6)
MIN_SCENE_DURATION = 15.0
MAX_SCENE_DURATION = 20.0

SCENE_SECTION_ALIASES: dict[str, str] = {
    "desenvolvimento_1": "desenvolvimento",
    "desenvolvimento_2": "desenvolvimento",
    "impacto": "consequencias",
}


def apply_timeline_to_scenes(
    scenes_data: dict | list,
    timeline: EmotionalTimeline,
) -> dict:
    """
    Enriquece cenas com dados emocionais e visuais da timeline compartilhada.
    Distribui durações reais da timeline entre cenas que compartilham seção.
    """

    if isinstance(scenes_data, dict):
        result = dict(scenes_data)
        scenes = list(result.get("cenas", []))
    else:
        result = {"cenas": list(scenes_data or [])}
        scenes = result["cenas"]

    if not scenes:
        result["cenas"] = scenes
        result["emotional_timeline"] = timeline.to_dict()
        return result

    sections_by_key = {
        section.section_key: section
        for section in timeline.sections
        if section.section_key
    }

    section_scene_groups: dict[str, list[int]] = {}
    for index, scene in enumerate(scenes):
        key = _section_key_for_scene(scene)
        section_scene_groups.setdefault(key, []).append(index)

    mapper = get_emotion_mapper()
    current_time = 0.0
    audio_duration = float(timeline.total_duration or 0.0)

    for index, scene in enumerate(scenes):
        section_key = _section_key_for_scene(scene)
        section = sections_by_key.get(section_key)
        if not section:
            section = _match_timeline_section(index, timeline.sections, scene)

        if not section:
            remaining = len(scenes) - index
            remaining_time = max(0.0, audio_duration - current_time)
            assigned = max(
                0.5,
                round(remaining_time / remaining, 2) if remaining else MIN_SCENE_DURATION,
            )
            scene["duration_seconds"] = assigned
            scene["duration_hint"] = assigned
            scene["tempo_inicio"] = round(current_time, 2)
            scene["tempo_fim"] = round(current_time + assigned, 2)
            scene["tempo"] = f"{int(current_time)}-{int(current_time + assigned)}"
            current_time = round(current_time + assigned, 2)
            continue

        group_indices = section_scene_groups.get(section_key, [index])
        group_position = group_indices.index(index)
        group_size = len(group_indices)

        section_duration = section.real_duration or section.duration
        if section_duration <= 0:
            section_duration = section.estimated_duration or 0.0

        if group_size > 1 and section_duration > 0:
            share = section_duration / group_size
            if group_position == group_size - 1:
                assigned = max(0.5, round(section_duration - share * (group_size - 1), 2))
            else:
                assigned = max(0.5, round(share, 2))
        else:
            assigned = max(0.5, round(section_duration, 2))

        if index == len(scenes) - 1 and audio_duration > 0:
            assigned = max(0.5, round(audio_duration - current_time, 2))

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

        scene["duration_seconds"] = assigned
        scene["duration_hint"] = assigned
        scene["tempo_inicio"] = round(current_time, 2)
        scene["tempo_fim"] = round(current_time + assigned, 2)
        scene["tempo"] = f"{int(current_time)}-{int(current_time + assigned)}"

        current_time = round(current_time + assigned, 2)

    if audio_duration > 0 and scenes:
        delta = round(audio_duration - current_time, 2)
        if abs(delta) >= 0.01 and scenes[-1].get("duration_seconds"):
            last = scenes[-1]
            last["duration_seconds"] = max(0.5, round(last["duration_seconds"] + delta, 2))
            last["duration_hint"] = last["duration_seconds"]
            last["tempo_fim"] = round(last["tempo_inicio"] + last["duration_seconds"], 2)
            last["tempo"] = f"{int(last['tempo_inicio'])}-{int(last['tempo_fim'])}"

    result["cenas"] = scenes
    result["audio_duration"] = round(audio_duration, 2) if audio_duration else round(current_time, 2)
    result["synced"] = bool(timeline.director_meta.get("synced_to_audio"))
    result["emotional_timeline"] = timeline.to_dict()
    return result


def _section_key_for_scene(scene: dict) -> str:
    scene_type = scene.get("tipo", "")
    return SCENE_SECTION_ALIASES.get(scene_type, scene_type)


def _match_timeline_section(
    scene_index: int,
    sections: list[TimelineSection],
    scene: dict,
) -> Optional[TimelineSection]:
    scene_key = _section_key_for_scene(scene)

    for section in sections:
        if section.section_key and section.section_key == scene_key:
            return section

    if scene_index < len(sections):
        return sections[scene_index]

    return None


def get_scene_render_hints(scene: dict) -> dict[str, Any]:
    """
    Retorna hints de renderização baseados na emoção e visual intent da cena.
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
