"""
Visual Intent Engine — traduz narrativa em intenção visual para busca de mídia.

Separa emoção (prosódia/TTS) de intenção visual (assets/câmera/paleta).
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Optional

from scripts.core.emotional_timeline import EmotionalTimeline, TimelineSection

# Termos que devem ser evitados em QUALQUER cena, independente do provider.
# Usados apenas como fator complementar de busca/ranking (nunca filtro absoluto).
_GLOBAL_AVOID: list[str] = [
    "text overlay",
    "watermark",
    "logo",
    "caption",
    "cartoon",
    "collage",
]

# Cada intenção visual carrega, além dos campos originais (asset_priority,
# color_palette, search_suffix), metadados narrativos que nascem do fluxo
# Strategy -> Emotional Timeline -> Visual Intent:
#   visual_goal  — objetivo visual do momento narrativo
#   lighting     — qualidade de luz coerente com a emoção
#   style        — estilo geral do plano
#   avoid        — termos a penalizar (complementa _GLOBAL_AVOID)
INTENT_SPECS: dict[str, dict[str, Any]] = {
    "dramatic_opening": {
        "asset_priority": ["archive_video", "stock_video", "historical_photo", "engraving"],
        "color_palette": "warm_dramatic",
        "search_suffix": "dramatic cinematic opening documentary",
        "visual_goal": "impactful close-up contrast",
        "lighting": "high contrast dramatic",
        "style": "cinematic",
        "avoid": ["static", "empty landscape"],
    },
    "historical_context": {
        "asset_priority": ["historical_photo", "old_map", "engraving", "archive_video", "stock_video"],
        "color_palette": "sepia",
        "search_suffix": "historical context documentary establishing",
        "visual_goal": "establishing environment architecture",
        "lighting": "natural soft",
        "style": "documentary",
        "avoid": ["extreme close-up"],
    },
    "investigation": {
        "asset_priority": ["archive_video", "historical_photo", "old_map", "stock_video"],
        "color_palette": "cold",
        "search_suffix": "investigation research documentary",
        "visual_goal": "details process research",
        "lighting": "moody",
        "style": "documentary",
        "avoid": ["wide empty"],
    },
    "historical_event": {
        "asset_priority": ["archive_video", "historical_photo", "stock_video", "engraving"],
        "color_palette": "neutral",
        "search_suffix": "historical event documentary footage",
        "visual_goal": "dramatic movement event",
        "lighting": "natural",
        "style": "archival",
        "avoid": [],
    },
    "dramatic_reveal": {
        "asset_priority": ["archive_video", "historical_photo", "engraving", "stock_video"],
        "color_palette": "high_contrast",
        "search_suffix": "dramatic reveal documentary close up",
        "visual_goal": "drama movement tension",
        "lighting": "high contrast",
        "style": "cinematic",
        "avoid": ["flat", "static"],
    },
    "impact_consequences": {
        "asset_priority": ["stock_video", "archive_video", "historical_photo"],
        "color_palette": "desaturated",
        "search_suffix": "impact consequences documentary",
        "visual_goal": "aftermath scale",
        "lighting": "desaturated",
        "style": "documentary",
        "avoid": [],
    },
    "legacy_impact": {
        "asset_priority": ["stock_video", "historical_photo", "archive_video"],
        "color_palette": "modern_cold",
        "search_suffix": "legacy modern impact documentary",
        "visual_goal": "modern legacy contrast",
        "lighting": "cool",
        "style": "cinematic",
        "avoid": [],
    },
    "atmospheric_closing": {
        "asset_priority": ["stock_video", "historical_photo", "engraving"],
        "color_palette": "muted",
        "search_suffix": "cinematic closing atmospheric documentary",
        "visual_goal": "contemplation closing",
        "lighting": "soft muted",
        "style": "cinematic",
        "avoid": ["busy", "chaotic"],
    },
    "ancient_ruins": {
        "asset_priority": ["historical_photo", "engraving", "old_map", "archive_video", "stock_video"],
        "color_palette": "cold",
        "search_suffix": "ancient ruins mystery documentary",
        "visual_goal": "ancient mystery detail",
        "lighting": "cold atmospheric",
        "style": "cinematic",
        "avoid": ["modern", "urban"],
    },
    "general_narrative": {
        "asset_priority": ["stock_video", "historical_photo", "archive_video"],
        "color_palette": "neutral",
        "search_suffix": "documentary cinematic footage",
        "visual_goal": "",
        "lighting": "",
        "style": "documentary",
        "avoid": [],
    },
    # --- Intenções emocionais (fallback a partir da emoção em script_parser) ---
    "dramatic_event": {
        "asset_priority": ["archive_video", "stock_video", "historical_photo"],
        "color_palette": "warm_dramatic",
        "search_suffix": "dramatic event footage",
        "visual_goal": "dramatic movement",
        "lighting": "dramatic",
        "style": "cinematic",
        "avoid": ["static"],
    },
    "peaceful_landscape": {
        "asset_priority": ["stock_video", "historical_photo"],
        "color_palette": "muted",
        "search_suffix": "peaceful landscape nature",
        "visual_goal": "calm establishing environment",
        "lighting": "soft natural",
        "style": "cinematic",
        "avoid": ["chaotic"],
    },
    "tension_scene": {
        "asset_priority": ["stock_video", "archive_video"],
        "color_palette": "high_contrast",
        "search_suffix": "tension dramatic scene",
        "visual_goal": "tension movement",
        "lighting": "high contrast",
        "style": "cinematic",
        "avoid": ["calm"],
    },
    "melancholy_archive": {
        "asset_priority": ["historical_photo", "archive_video"],
        "color_palette": "desaturated",
        "search_suffix": "melancholy archive footage",
        "visual_goal": "reflective detail",
        "lighting": "muted",
        "style": "archival",
        "avoid": [],
    },
    # --- Intenções TikTok/produto (rule-based, sem viés de provider) ---
    "attention_grab": {
        "asset_priority": ["stock_video"],
        "color_palette": "high_contrast",
        "search_suffix": "dynamic attention grabbing",
        "visual_goal": "impactful close-up",
        "lighting": "bright",
        "style": "dynamic",
        "avoid": [],
    },
    "problem_setup": {
        "asset_priority": ["stock_video"],
        "color_palette": "neutral",
        "search_suffix": "problem context lifestyle",
        "visual_goal": "problem context",
        "lighting": "natural",
        "style": "lifestyle",
        "avoid": [],
    },
    "product_demo": {
        "asset_priority": ["stock_video"],
        "color_palette": "neutral",
        "search_suffix": "product demonstration close up",
        "visual_goal": "product in use detail",
        "lighting": "clean bright",
        "style": "product",
        "avoid": [],
    },
    "result_showcase": {
        "asset_priority": ["stock_video"],
        "color_palette": "warm_dramatic",
        "search_suffix": "positive result showcase",
        "visual_goal": "positive result reveal",
        "lighting": "warm bright",
        "style": "lifestyle",
        "avoid": [],
    },
    "call_to_action": {
        "asset_priority": ["stock_video"],
        "color_palette": "neutral",
        "search_suffix": "product showcase",
        "visual_goal": "product showcase",
        "lighting": "bright",
        "style": "product",
        "avoid": [],
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
    "static": "parallax_left",
}

# Enquadramento (termo de busca real, presente em bancos de mídia) derivado
# da câmera resolvida. Mantém a query concreta e não abstrata.
_CAMERA_FRAMING: dict[str, str] = {
    "zoom_in_center": "close up",
    "zoom_out_center": "wide establishing shot",
    "pan_right": "sweeping pan",
    "pan_left": "sweeping pan",
    "parallax_left": "wide shot",
}


def camera_framing(camera: str) -> str:
    """Traduz a câmera resolvida em um termo de enquadramento pesquisável."""

    return _CAMERA_FRAMING.get(camera, "")


@dataclass
class VisualIntentSpec:
    visual_intent: str
    asset_priority: list[str]
    color_palette: str
    camera: str
    search_query_suffix: str = ""
    visual_goal: str = ""
    lighting: str = ""
    style: str = ""
    avoid: list[str] = field(default_factory=list)

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

    # avoid nasce do global + específico da intenção, sem duplicatas
    avoid = list(dict.fromkeys(_GLOBAL_AVOID + list(spec_data.get("avoid", []))))

    return VisualIntentSpec(
        visual_intent=intent_key,
        asset_priority=list(spec_data["asset_priority"]),
        color_palette=spec_data.get("color_palette") or EMOTION_PALETTE.get(emotion, "neutral"),
        camera=CAMERA_ALIASES.get(camera, camera),
        search_query_suffix=spec_data.get("search_suffix", ""),
        visual_goal=spec_data.get("visual_goal", ""),
        lighting=spec_data.get("lighting", ""),
        style=spec_data.get("style", ""),
        avoid=avoid,
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
    base = base_query.strip()
    parts = [base]
    seen = base.lower()

    def _add(fragment: str) -> None:
        fragment = fragment.strip()
        if not fragment:
            return
        # evita repetir termos já presentes na query
        new_words = [w for w in fragment.split() if w.lower() not in seen]
        if not new_words:
            return
        added = " ".join(new_words)
        parts.append(added)
        # atualiza o conjunto de palavras vistas
        nonlocal seen
        seen = f"{seen} {added.lower()}"

    # objetivo visual do momento narrativo (mantém a query concreta)
    _add(spec.visual_goal)
    # enquadramento concreto derivado da câmera
    _add(camera_framing(spec.camera))
    # sufixo original da intenção
    _add(spec.search_query_suffix)

    palette_hints = {
        "cold": "blue tones atmospheric",
        "warm_dramatic": "warm dramatic lighting",
        "sepia": "vintage sepia historical",
        "high_contrast": "high contrast dramatic",
        "desaturated": "desaturated moody",
        "muted": "soft muted atmospheric",
    }
    _add(palette_hints.get(spec.color_palette, ""))

    return " ".join(p for p in parts if p)


def get_timeline_visual_specs(timeline: EmotionalTimeline) -> list[VisualIntentSpec]:
    """Retorna specs visuais para todas as seções."""

    return [resolve_visual_intent(section) for section in timeline.sections]
