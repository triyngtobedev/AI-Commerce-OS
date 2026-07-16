"""
Visual Intent Engine — traduz narrativa em intenção visual para busca de mídia.

Separa emoção (prosódia/TTS) de intenção visual (assets/câmera/paleta).
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional

from scripts.core.emotional_timeline import EmotionalTimeline, TimelineSection

INTENT_SPECS: dict[str, dict[str, Any]] = {
    "dramatic_opening": {
        "asset_priority": ["archive_video", "stock_video", "historical_photo", "engraving"],
        "color_palette": "warm_dramatic",
        "search_suffix": "dramatic cinematic opening documentary",
    },
    "historical_context": {
        "asset_priority": ["historical_photo", "old_map", "engraving", "archive_video", "stock_video"],
        "color_palette": "sepia",
        "search_suffix": "historical context documentary establishing",
    },
    "investigation": {
        "asset_priority": ["archive_video", "historical_photo", "old_map", "stock_video"],
        "color_palette": "cold",
        "search_suffix": "investigation research documentary",
    },
    "historical_event": {
        "asset_priority": ["archive_video", "historical_photo", "stock_video", "engraving"],
        "color_palette": "neutral",
        "search_suffix": "historical event documentary footage",
    },
    "dramatic_reveal": {
        "asset_priority": ["archive_video", "historical_photo", "engraving", "stock_video"],
        "color_palette": "high_contrast",
        "search_suffix": "dramatic reveal documentary close up",
    },
    "impact_consequences": {
        "asset_priority": ["stock_video", "archive_video", "historical_photo"],
        "color_palette": "desaturated",
        "search_suffix": "impact consequences documentary",
    },
    "legacy_impact": {
        "asset_priority": ["stock_video", "historical_photo", "archive_video"],
        "color_palette": "modern_cold",
        "search_suffix": "legacy modern impact documentary",
    },
    "atmospheric_closing": {
        "asset_priority": ["stock_video", "historical_photo", "engraving"],
        "color_palette": "muted",
        "search_suffix": "cinematic closing atmospheric documentary",
    },
    "ancient_ruins": {
        "asset_priority": ["historical_photo", "engraving", "old_map", "archive_video", "stock_video"],
        "color_palette": "cold",
        "search_suffix": "ancient ruins mystery documentary",
    },
    "general_narrative": {
        "asset_priority": ["stock_video", "historical_photo", "archive_video"],
        "color_palette": "neutral",
        "search_suffix": "documentary cinematic footage",
    },
}

EMOTION_PALETTE: dict[str, str] = {
    "mystery": "cold",
    "impact": "warm_dramatic",
    "calm": "muted",
    "warning": "high_contrast",
    "sad": "desaturated",
    "neutral": "neutral",
}

CAMERA_ALIASES: dict[str, str] = {
    "slow_push": "zoom_in_center",
    "fast_zoom": "zoom_in_center",
    "slow_pan": "pan_right",
    "slow_pull": "zoom_out_center",
    "shake_light": "pan_left",
    "static": "pan_right",
}


@dataclass
class VisualIntentSpec:
    visual_intent: str
    asset_priority: list[str]
    color_palette: str
    camera: str
    search_query_suffix: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_visual_intent(
    section: TimelineSection | dict,
) -> VisualIntentSpec:
    """Resolve especificação visual para uma seção."""

    if isinstance(section, TimelineSection):
        intent_key = section.visual_intent
        emotion = section.emotion
        camera = section.camera_motion
    else:
        intent_key = section.get("visual_intent", "general_narrative")
        emotion = section.get("emotion", "calm")
        camera = section.get("camera_motion", "slow_push")

    spec_data = INTENT_SPECS.get(intent_key, INTENT_SPECS["general_narrative"])

    return VisualIntentSpec(
        visual_intent=intent_key,
        asset_priority=list(spec_data["asset_priority"]),
        color_palette=spec_data.get("color_palette") or EMOTION_PALETTE.get(emotion, "neutral"),
        camera=CAMERA_ALIASES.get(camera, camera),
        search_query_suffix=spec_data.get("search_suffix", ""),
    )


def apply_visual_intents(timeline: EmotionalTimeline) -> EmotionalTimeline:
    """
    Enriquece cada seção da timeline com especificação visual.
    Não recalcula emoções — apenas adiciona metadados visuais.
    """

    for section in timeline.sections:
        spec = resolve_visual_intent(section)
        if not section.visual_intent or section.visual_intent == "general_narrative":
            section.visual_intent = spec.visual_intent

    timeline.director_meta.setdefault("visual_intents_applied", True)
    return timeline


def build_visual_search_query(
    base_query: str,
    section: TimelineSection | dict,
) -> str:
    """Constrói query de busca enriquecida com intenção visual."""

    spec = resolve_visual_intent(section)
    parts = [base_query.strip()]

    if spec.search_query_suffix and spec.search_query_suffix not in base_query:
        parts.append(spec.search_query_suffix)

    palette_hints = {
        "cold": "blue tones atmospheric",
        "warm_dramatic": "warm dramatic lighting",
        "sepia": "vintage sepia historical",
        "high_contrast": "high contrast dramatic",
        "desaturated": "desaturated moody",
        "muted": "soft muted atmospheric",
    }
    hint = palette_hints.get(spec.color_palette, "")
    if hint:
        parts.append(hint)

    return " ".join(p for p in parts if p)


def get_timeline_visual_specs(timeline: EmotionalTimeline) -> list[VisualIntentSpec]:
    """Retorna specs visuais para todas as seções."""

    return [resolve_visual_intent(section) for section in timeline.sections]
