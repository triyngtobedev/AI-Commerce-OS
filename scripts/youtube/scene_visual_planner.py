"""
Scene Visual Planner — enriquece cenas com plano visual editorial completo.

Campos: scene_type, visual_intent, must_show, avoid_showing, asset_queries,
fallback_visual_plan, emotion, pace, on_screen_text, thumbnail_potential, broll_density.
"""

from __future__ import annotations

from typing import Any, Optional

from scripts.video.visual_grammar import (
    _LEGACY_TYPE_MAP,
    resolve_editorial_scene_type,
)
from scripts.video.query_localizer import localize_search_query


_SCENE_DEFAULTS: dict[str, dict] = {
    "hook": {
        "visual_intent": "dramatic_hook",
        "emotion": "impact",
        "pace": "fast",
        "broll_density": "high",
        "thumbnail_potential": True,
        "fallback_visual_plan": "ken_burns_montage",
    },
    "context": {
        "visual_intent": "establishing_context",
        "emotion": "curiosity",
        "pace": "medium",
        "broll_density": "medium",
        "thumbnail_potential": False,
        "fallback_visual_plan": "ken_burns",
    },
    "conflict": {
        "visual_intent": "tension_conflict",
        "emotion": "tension",
        "pace": "fast",
        "broll_density": "high",
        "thumbnail_potential": False,
        "fallback_visual_plan": "ken_burns",
    },
    "character": {
        "visual_intent": "portrait_subject",
        "emotion": "curiosity",
        "pace": "medium",
        "broll_density": "medium",
        "thumbnail_potential": True,
        "fallback_visual_plan": "ken_burns",
    },
    "data": {
        "visual_intent": "data_visualization",
        "emotion": "impact",
        "pace": "medium",
        "broll_density": "low",
        "thumbnail_potential": False,
        "fallback_visual_plan": "animated_chart",
    },
    "timeline": {
        "visual_intent": "chronological_events",
        "emotion": "curiosity",
        "pace": "medium",
        "broll_density": "medium",
        "thumbnail_potential": False,
        "fallback_visual_plan": "animated_timeline",
    },
    "map": {
        "visual_intent": "geographic_context",
        "emotion": "curiosity",
        "pace": "slow",
        "broll_density": "low",
        "thumbnail_potential": False,
        "fallback_visual_plan": "animated_map",
    },
    "turning_point": {
        "visual_intent": "dramatic_reveal",
        "emotion": "revelation",
        "pace": "fast",
        "broll_density": "high",
        "thumbnail_potential": True,
        "fallback_visual_plan": "ken_burns_aggressive",
    },
    "climax": {
        "visual_intent": "impact_climax",
        "emotion": "impact",
        "pace": "fast",
        "broll_density": "high",
        "thumbnail_potential": True,
        "fallback_visual_plan": "montage",
    },
    "resolution": {
        "visual_intent": "closing_reflection",
        "emotion": "calm",
        "pace": "slow",
        "broll_density": "low",
        "thumbnail_potential": False,
        "fallback_visual_plan": "ken_burns",
    },
    "evidence": {
        "visual_intent": "document_proof",
        "emotion": "curiosity",
        "pace": "medium",
        "broll_density": "medium",
        "thumbnail_potential": False,
        "fallback_visual_plan": "document_highlight",
    },
}


def _generate_asset_queries(scene: dict, topic: str, research_pack: Optional[dict] = None) -> list[str]:
    """Gera queries de busca para a cena."""

    visual = scene.get("visual", "")
    must_show = scene.get("must_show", visual)
    editorial = resolve_editorial_scene_type(scene)

    queries = [localize_search_query(must_show or visual)]

    if research_pack:
        en_terms = research_pack.get("real_image_search_terms_en", [])
        for term in en_terms[:2]:
            queries.append(localize_search_query(f"{term} {editorial}"))

    type_queries = {
        "data": ["statistics chart infographic", "growth graph business"],
        "map": ["world map logistics route", "geographic supply chain"],
        "timeline": ["historical timeline events", "chronology documentary"],
        "evidence": ["newspaper headline document", "official document archive"],
        "hook": ["dramatic factory aerial", "fast fashion warehouse"],
    }
    queries.extend(type_queries.get(editorial, [f"{topic} documentary footage"]))

    # Dedup preserving order
    seen = set()
    unique = []
    for q in queries:
        key = q.lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(q)

    return unique[:8]


def enrich_scene_visual_plan(
    scene: dict,
    *,
    topic: str = "",
    index: int = 0,
    research_pack: Optional[dict] = None,
    script_section: Optional[str] = None,
) -> dict:
    """Enriquece uma cena com plano visual editorial."""

    enriched = dict(scene)
    editorial_type = resolve_editorial_scene_type(enriched)
    defaults = _SCENE_DEFAULTS.get(editorial_type, _SCENE_DEFAULTS["context"])

    enriched.setdefault("scene_type", editorial_type)
    enriched.setdefault("visual_intent", defaults["visual_intent"])
    enriched.setdefault("emotion", defaults["emotion"])
    enriched.setdefault("pace", defaults["pace"])
    enriched.setdefault("broll_density", defaults["broll_density"])
    enriched.setdefault("thumbnail_potential", defaults["thumbnail_potential"])
    enriched.setdefault("fallback_visual_plan", defaults["fallback_visual_plan"])

    visual = enriched.get("visual", "")
    enriched.setdefault("must_show", visual or script_section[:80] if script_section else topic)
    enriched.setdefault("avoid_showing", ["watermark", "logo", "text overlay", "meme", "tiktok"])

    if script_section and not enriched.get("on_screen_text"):
        # Extrai frase impactante para overlay
        sentences = [s.strip() for s in script_section.replace("[PAUSA]", "").split(".") if s.strip()]
        if sentences and editorial_type in ("hook", "turning_point", "data"):
            enriched["on_screen_text"] = sentences[0][:60]

    enriched["asset_queries"] = _generate_asset_queries(enriched, topic, research_pack)

    return enriched


def enrich_scenes_with_visual_plan(
    scenes: dict,
    *,
    topic: str = "",
    research_pack: Optional[dict] = None,
    script: Optional[dict] = None,
) -> dict:
    """Aplica plano visual a todas as cenas."""

    script = script or {}
    section_keys = ["hook", "contexto", "desenvolvimento", "revelacao", "consequencias", "encerramento"]

    updated = dict(scenes)
    enriched_cenas = []

    for i, scene in enumerate(scenes.get("cenas", [])):
        section_key = scene.get("tipo", section_keys[min(i, len(section_keys) - 1)])
        script_text = script.get(section_key, "") if script else scene.get("narracao", "")

        enriched_cenas.append(enrich_scene_visual_plan(
            scene,
            topic=topic or scenes.get("produto", ""),
            index=i,
            research_pack=research_pack,
            script_section=script_text,
        ))

    updated["cenas"] = enriched_cenas
    updated["visual_plan_version"] = 2
    return updated
