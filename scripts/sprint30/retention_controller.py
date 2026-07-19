"""Otimizações de retenção pré-render e predição pós-produção."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.core.emotional_timeline import EmotionalTimeline
from scripts.core.emotional_effects import get_section_effect_hints
from scripts.sprint30.config import is_retention_controller_enabled

HOOK_SCENE_TYPES = {"hook", "gancho", "abertura", "intro"}
IMPACT_SCENE_TYPES = {"impacto", "revelacao", "climax"}


def apply_retention_optimizations(
    scenes_data: dict,
    timeline: EmotionalTimeline | dict,
) -> dict:
    """
    Reforça hook e pacing nas primeiras cenas quando RETENTION_CONTROLLER=true.
    Retorna scenes_data com retention_actions anotadas.
    """

    if not is_retention_controller_enabled():
        return scenes_data

    result = dict(scenes_data)
    scenes = list(result.get("cenas", []))
    sections = _timeline_sections(timeline)
    actions: list[str] = []

    for index, scene in enumerate(scenes):
        section = sections[index] if index < len(sections) else None
        hints = dict(scene.get("effect_hints") or {})
        if section:
            hints = dict(get_section_effect_hints(section))

        tipo = str(scene.get("tipo", "")).lower()
        is_hook = index == 0 or tipo in HOOK_SCENE_TYPES
        is_impact = tipo in IMPACT_SCENE_TYPES

        if is_hook:
            hints.setdefault("effects", [])
            for effect in ("flash", "zoom"):
                if effect not in hints["effects"]:
                    hints["effects"].append(effect)
            hints["flash_enabled"] = True
            hints["zoom_intensity"] = max(float(hints.get("zoom_intensity", 0)), 0.18)
            hints["camera_motion"] = hints.get("camera_motion") or "slow_push"
            scene["scene_motion"] = scene.get("scene_motion") or "ken_burns_push"
            actions.append(f"hook_boost_scene_{index + 1}")

        elif is_impact and index <= 2:
            hints.setdefault("effects", [])
            if "shake" not in hints["effects"]:
                hints["effects"].append("shake")
            hints["shake_enabled"] = True
            actions.append(f"impact_boost_scene_{index + 1}")

        scene["effect_hints"] = hints

    result["cenas"] = scenes
    result["retention_actions"] = actions
    return result


def predict_retention(
    export_folder: Path,
    result: dict,
    *,
    quality_report: dict | None = None,
    health_report: dict | None = None,
) -> dict[str, Any]:
    """
    Estima retenção com base em sinais pré-publicação.
    Não substitui YouTube Analytics — serve ao batch Sprint 30.
    """

    scenes = result.get("cenas", {}).get("cenas", [])
    if not isinstance(scenes, list):
        scenes = []

    hook_has_motion = _hook_has_motion(scenes)
    video_ratio = _video_scene_ratio(export_folder)
    rhythm_score = _dimension_score(quality_report, "rhythm")
    motion_score = _dimension_score(quality_report, "motion_coverage")
    thumbnail_score = _dimension_score(quality_report, "thumbnail")
    caption_score = _dimension_score(quality_report, "caption_quality")
    sync_ok = _audio_sync_ok(health_report)

    score = 42.0
    score += 12.0 if hook_has_motion else 0.0
    score += min(18.0, video_ratio * 30.0)
    score += rhythm_score * 0.12
    score += motion_score * 0.08
    score += thumbnail_score * 0.10
    score += caption_score * 0.05
    score += 6.0 if sync_ok else -8.0

    score = max(15.0, min(92.0, round(score, 1)))
    actions_count = len(result.get("cenas", {}).get("retention_actions", []))

    return {
        "retention_predicted_score": score,
        "retention_predicted_label": _retention_label(score),
        "retention_actions_count": actions_count,
        "retention_signals": {
            "hook_has_motion": hook_has_motion,
            "video_scene_ratio": round(video_ratio, 3),
            "audio_sync_ok": sync_ok,
        },
    }


def _timeline_sections(timeline: EmotionalTimeline | dict) -> list:
    if isinstance(timeline, EmotionalTimeline):
        return timeline.sections
    if isinstance(timeline, dict):
        return timeline.get("sections", [])
    return []


def _hook_has_motion(scenes: list) -> bool:
    if not scenes:
        return False
    hook = scenes[0] if isinstance(scenes[0], dict) else {}
    hints = hook.get("effect_hints") or {}
    return bool(
        hook.get("scene_motion")
        or hook.get("camera_motion")
        or hook.get("visual_spec")
        or hints.get("zoom_intensity")
        or "zoom" in (hints.get("effects") or [])
    )


def _video_scene_ratio(export_folder: Path) -> float:
    media_search = export_folder / "assets" / "media_search.json"
    if not media_search.exists():
        return 0.0

    import json

    data = json.loads(media_search.read_text(encoding="utf-8"))
    scene_rows = data.get("scenes", [])
    if not scene_rows:
        return 0.0

    video_types = {"video", "ai_video"}
    video_count = sum(
        1 for row in scene_rows
        if row.get("saved") and row.get("media_type") in video_types
    )
    return video_count / len(scene_rows)


def _dimension_score(quality_report: dict | None, name: str) -> float:
    if not quality_report:
        return 50.0
    for row in quality_report.get("dimensions", []):
        if row.get("dimension") == name:
            return float(row.get("score", 50.0))
    return 50.0


def _audio_sync_ok(health_report: dict | None) -> bool:
    if not health_report:
        return True
    for check in health_report.get("checks", []):
        if check.get("check") == "audio_video_sync":
            return bool(check.get("passed"))
    return True


def _retention_label(score: float) -> str:
    if score >= 75:
        return "strong"
    if score >= 55:
        return "moderate"
    if score >= 40:
        return "weak"
    return "at_risk"
