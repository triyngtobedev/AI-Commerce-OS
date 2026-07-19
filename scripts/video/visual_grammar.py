"""
Visual Grammar — regras editoriais por tipo de cena documental.

Cada tipo de cena recebe motion, composição e overlays distintos
para evitar aparência de slideshow genérico.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional

# Tipos editoriais canônicos
EDITORIAL_SCENE_TYPES = (
    "hook",
    "context",
    "character",
    "conflict",
    "data",
    "timeline",
    "map",
    "quote",
    "evidence",
    "turning_point",
    "climax",
    "resolution",
)

# Mapeamento tipos legados do pipeline → tipos editoriais
_LEGACY_TYPE_MAP = {
    "hook": "hook",
    "gancho": "hook",
    "contexto": "context",
    "desenvolvimento": "conflict",
    "desenvolvimento_1": "conflict",
    "desenvolvimento_2": "character",
    "revelacao": "turning_point",
    "revelacao_p2": "turning_point",
    "consequencias": "climax",
    "impacto": "data",
    "encerramento": "resolution",
    "demonstracao": "evidence",
    "beneficio": "resolution",
    "cta": "hook",
}


@dataclass
class VisualGrammarSpec:
    scene_type: str
    motion_style: str
    camera_move: str
    cut_pace: str  # fast | medium | slow
    zoom_intensity: float
    parallax_layers: int
    overlay_type: str  # none | headline | data | timeline | map | quote | evidence
    grain: bool
    light_sweep: bool
    crossfade: float
    ken_burns: bool
    montage_count: int
    on_screen_text_style: str
    sound_impact: bool

    def to_dict(self) -> dict:
        return asdict(self)


_GRAMMAR_BY_TYPE: dict[str, VisualGrammarSpec] = {
    "hook": VisualGrammarSpec(
        scene_type="hook",
        motion_style="aggressive_zoom",
        camera_move="zoom_in_center",
        cut_pace="fast",
        zoom_intensity=1.25,
        parallax_layers=2,
        overlay_type="headline",
        grain=True,
        light_sweep=True,
        crossfade=0.3,
        ken_burns=True,
        montage_count=3,
        on_screen_text_style="bold_large",
        sound_impact=True,
    ),
    "context": VisualGrammarSpec(
        scene_type="context",
        motion_style="slow_establishing",
        camera_move="zoom_out_center",
        cut_pace="medium",
        zoom_intensity=1.08,
        parallax_layers=1,
        overlay_type="none",
        grain=False,
        light_sweep=False,
        crossfade=0.6,
        ken_burns=True,
        montage_count=1,
        on_screen_text_style="subtitle",
        sound_impact=False,
    ),
    "character": VisualGrammarSpec(
        scene_type="character",
        motion_style="portrait_push",
        camera_move="slow_push",
        cut_pace="medium",
        zoom_intensity=1.12,
        parallax_layers=2,
        overlay_type="none",
        grain=True,
        light_sweep=False,
        crossfade=0.5,
        ken_burns=True,
        montage_count=1,
        on_screen_text_style="name_card",
        sound_impact=False,
    ),
    "conflict": VisualGrammarSpec(
        scene_type="conflict",
        motion_style="dynamic_pan",
        camera_move="pan_right",
        cut_pace="fast",
        zoom_intensity=1.15,
        parallax_layers=2,
        overlay_type="none",
        grain=True,
        light_sweep=True,
        crossfade=0.4,
        ken_burns=True,
        montage_count=2,
        on_screen_text_style="none",
        sound_impact=False,
    ),
    "data": VisualGrammarSpec(
        scene_type="data",
        motion_style="static_with_motion_graphics",
        camera_move="static",
        cut_pace="medium",
        zoom_intensity=1.0,
        parallax_layers=0,
        overlay_type="data",
        grain=False,
        light_sweep=False,
        crossfade=0.5,
        ken_burns=False,
        montage_count=1,
        on_screen_text_style="data_large",
        sound_impact=False,
    ),
    "timeline": VisualGrammarSpec(
        scene_type="timeline",
        motion_style="horizontal_scroll",
        camera_move="pan_right",
        cut_pace="medium",
        zoom_intensity=1.05,
        parallax_layers=2,
        overlay_type="timeline",
        grain=True,
        light_sweep=False,
        crossfade=0.5,
        ken_burns=True,
        montage_count=3,
        on_screen_text_style="date_large",
        sound_impact=False,
    ),
    "map": VisualGrammarSpec(
        scene_type="map",
        motion_style="geo_zoom",
        camera_move="zoom_in_center",
        cut_pace="slow",
        zoom_intensity=1.20,
        parallax_layers=1,
        overlay_type="map",
        grain=False,
        light_sweep=False,
        crossfade=0.6,
        ken_burns=True,
        montage_count=1,
        on_screen_text_style="location_label",
        sound_impact=False,
    ),
    "quote": VisualGrammarSpec(
        scene_type="quote",
        motion_style="document_focus",
        camera_move="slow_push",
        cut_pace="slow",
        zoom_intensity=1.10,
        parallax_layers=1,
        overlay_type="quote",
        grain=True,
        light_sweep=True,
        crossfade=0.7,
        ken_burns=True,
        montage_count=1,
        on_screen_text_style="quote_highlight",
        sound_impact=False,
    ),
    "evidence": VisualGrammarSpec(
        scene_type="evidence",
        motion_style="document_scan",
        camera_move="zoom_in_center",
        cut_pace="medium",
        zoom_intensity=1.18,
        parallax_layers=1,
        overlay_type="evidence",
        grain=True,
        light_sweep=True,
        crossfade=0.5,
        ken_burns=True,
        montage_count=2,
        on_screen_text_style="highlight_marker",
        sound_impact=False,
    ),
    "turning_point": VisualGrammarSpec(
        scene_type="turning_point",
        motion_style="dramatic_reveal",
        camera_move="zoom_in_center",
        cut_pace="fast",
        zoom_intensity=1.22,
        parallax_layers=2,
        overlay_type="headline",
        grain=True,
        light_sweep=True,
        crossfade=0.35,
        ken_burns=True,
        montage_count=2,
        on_screen_text_style="bold_large",
        sound_impact=True,
    ),
    "climax": VisualGrammarSpec(
        scene_type="climax",
        motion_style="impact_montage",
        camera_move="dynamic",
        cut_pace="fast",
        zoom_intensity=1.20,
        parallax_layers=3,
        overlay_type="none",
        grain=True,
        light_sweep=True,
        crossfade=0.3,
        ken_burns=True,
        montage_count=4,
        on_screen_text_style="none",
        sound_impact=True,
    ),
    "resolution": VisualGrammarSpec(
        scene_type="resolution",
        motion_style="contemplative_drift",
        camera_move="zoom_out_center",
        cut_pace="slow",
        zoom_intensity=1.06,
        parallax_layers=1,
        overlay_type="none",
        grain=False,
        light_sweep=False,
        crossfade=0.8,
        ken_burns=True,
        montage_count=1,
        on_screen_text_style="subtitle",
        sound_impact=False,
    ),
}


def resolve_editorial_scene_type(scene: dict) -> str:
    """Resolve tipo editorial a partir de metadados da cena."""

    explicit = scene.get("scene_type", "")
    if explicit in _GRAMMAR_BY_TYPE:
        return explicit

    legacy = scene.get("tipo", "")
    return _LEGACY_TYPE_MAP.get(legacy, "context")


def get_visual_grammar(scene: dict) -> VisualGrammarSpec:
    """Retorna gramática visual para a cena."""

    editorial_type = resolve_editorial_scene_type(scene)
    spec = _GRAMMAR_BY_TYPE.get(editorial_type, _GRAMMAR_BY_TYPE["context"])

    # Ajustes por pace/emotion da cena
    pace = scene.get("pace", "")
    if pace == "fast":
        spec = VisualGrammarSpec(**{**spec.to_dict(), "cut_pace": "fast", "crossfade": max(0.25, spec.crossfade - 0.15)})
    elif pace == "slow":
        spec = VisualGrammarSpec(**{**spec.to_dict(), "cut_pace": "slow", "crossfade": min(1.0, spec.crossfade + 0.15)})

    return spec


def apply_visual_grammar_to_scene(scene: dict) -> dict:
    """Enriquece cena com spec de gramática visual para render."""

    spec = get_visual_grammar(scene)
    scene = dict(scene)
    scene["scene_type"] = resolve_editorial_scene_type(scene)
    scene["visual_grammar"] = spec.to_dict()
    scene.setdefault("scene_motion", spec.motion_style)
    scene.setdefault("camera_motion", spec.camera_move)
    scene.setdefault("crossfade_seconds", spec.crossfade)
    scene.setdefault("ken_burns_intensity", spec.zoom_intensity)
    scene.setdefault("overlay_type", spec.overlay_type)
    scene.setdefault("on_screen_text_style", spec.on_screen_text_style)
    return scene


def apply_visual_grammar_to_scenes(scenes: dict) -> dict:
    """Aplica gramática visual a todas as cenas."""

    updated = dict(scenes)
    updated["cenas"] = [
        apply_visual_grammar_to_scene(scene)
        for scene in scenes.get("cenas", [])
    ]
    return updated
