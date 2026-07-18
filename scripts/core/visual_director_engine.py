"""
Visual Director Engine — decide a estratégia visual de cada cena.

Recebe texto narrativo + metadados emocionais e retorna qual tipo de
visual representa melhor aquele momento (arquivo, mapa, documento, etc.).

Não busca mídia nem renderiza — apenas direção visual para downstream.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

SUPPORTED_ASSETS = frozenset({
    "archive_video",
    "animated_map",
    "documentary_image",
    "generated_visual",
    "ww2_archive_video",
    "europe_map",
    "military_documents",
    "historical_photo",
    "old_map",
})

VISUAL_TYPES = frozenset({
    "historical_documentary",
    "geographic_explanation",
    "emotional_moment",
    "investigation",
    "dramatic_event",
    "general_narrative",
})

ANIMATION_STRATEGIES = frozenset({
    "map_movement",
    "ken_burns",
    "archive_footage",
    "timeline",
    "crossfade",
    "static_hold",
})

_YEAR_RE = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b")

_GEO_KEYWORDS = (
    "mapa", "front", "fronte", "território", "territorio", "expansão", "expansao",
    "invasão", "invasao", "marcha", "cerco", "europa", "fronteira", "região", "regiao",
    "continente", "península", "peninsula", "operacao", "operação",
)

_BATTLE_KEYWORDS = (
    "batalha", "ataque", "bombardeio", "combate", "ofensiva", "defensiva",
    "barbarossa", "dday", "stalingrado", "normandia", "blitz", "guerra",
    "exército", "exercito", "tropas", "tanques", "artilharia", "naval",
)

_DOCUMENT_KEYWORDS = (
    "documento", "tratado", "ordem", "telegrama", "relatório", "relatorio",
    "assinatura", "decreto", "ultimato", "protocolo", "arquivo", "manuscrito",
)

_EMOTIONAL_KEYWORDS = (
    "morte", "massacre", "holocausto", "tragédia", "tragedia", "luto",
    "horror", "sofrimento", "vitimas", "vítimas", "genocidio", "genocídio",
)

_WW2_KEYWORDS = (
    "segunda guerra", "world war", "ww2", "wwii", "nazista", "nazi",
    "hitler", "stalin", "barbarossa", "holocausto", "auschwitz", "d-day",
    "aliados", "eixo", "blitzkrieg",
)

_DEFAULT_DURATION = 8.0


@dataclass
class VisualDirection:
    """Decisão de direção visual para uma cena."""

    visual_type: str = "general_narrative"
    emotion: str = "neutral"
    assets_needed: list[str] = field(default_factory=list)
    animation_strategy: str = "ken_burns"
    duration: float = _DEFAULT_DURATION
    primary_asset: str = "archive_video"
    scene_text: str = ""
    section_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize(text: str) -> str:
    return text.lower().strip()


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(kw in text for kw in keywords)


def _resolve_emotion(scene: dict, text: str) -> str:
    explicit = scene.get("emotion", "")
    if explicit:
        emotion_map = {
            "mystery": "tension",
            "impact": "tension",
            "warning": "tension",
            "sad": "sorrow",
            "calm": "neutral",
        }
        return emotion_map.get(explicit, explicit)

    if _contains_any(text, _EMOTIONAL_KEYWORDS):
        return "sorrow"
    if _contains_any(text, _BATTLE_KEYWORDS):
        return "tension"
    if _contains_any(text, _GEO_KEYWORDS):
        return "neutral"
    return "neutral"


def _ww2_assets(text: str) -> list[str]:
    assets: list[str] = []
    if _contains_any(text, _WW2_KEYWORDS) or _YEAR_RE.search(text):
        assets.append("ww2_archive_video")
    if _contains_any(text, _GEO_KEYWORDS + _WW2_KEYWORDS):
        assets.append("europe_map")
    if _contains_any(text, _BATTLE_KEYWORDS):
        assets.append("military_documents")
    return assets


def _resolve_visual_type(text: str, scene: dict) -> tuple[str, str, str]:
    """
    Retorna (visual_type, primary_asset, animation_strategy).
    """

    section = scene.get("tipo", scene.get("section_key", ""))

    has_geo = _contains_any(text, _GEO_KEYWORDS)
    has_battle = _contains_any(text, _BATTLE_KEYWORDS)
    has_doc = _contains_any(text, _DOCUMENT_KEYWORDS)
    has_emotional = _contains_any(text, _EMOTIONAL_KEYWORDS)
    has_year = bool(_YEAR_RE.search(text))

    if section in ("contexto",) and has_geo:
        return "geographic_explanation", "animated_map", "map_movement"

    if has_battle and (has_geo or has_year):
        return "historical_documentary", "animated_map", "map_movement"

    if has_battle:
        return "dramatic_event", "archive_video", "archive_footage"

    if has_doc:
        return "investigation", "documentary_image", "ken_burns"

    if has_emotional:
        return "emotional_moment", "archive_video", "archive_footage"

    if has_geo:
        return "geographic_explanation", "animated_map", "map_movement"

    if section in ("revelacao", "hook") and has_year:
        return "dramatic_event", "archive_video", "archive_footage"

    intent = scene.get("visual_intent", "")
    intent_map = {
        "historical_context": ("historical_documentary", "documentary_image", "ken_burns"),
        "historical_event": ("dramatic_event", "archive_video", "archive_footage"),
        "dramatic_reveal": ("dramatic_event", "archive_video", "archive_footage"),
        "investigation": ("investigation", "documentary_image", "ken_burns"),
        "ancient_ruins": ("historical_documentary", "documentary_image", "ken_burns"),
        "old_map": ("geographic_explanation", "animated_map", "map_movement"),
    }
    if intent in intent_map:
        return intent_map[intent]

    return "general_narrative", "archive_video", "ken_burns"


def _build_assets_needed(
    text: str,
    primary_asset: str,
    visual_type: str,
) -> list[str]:
    assets: list[str] = []
    seen: set[str] = set()

    def _add(*items: str) -> None:
        for item in items:
            if item not in seen:
                seen.add(item)
                assets.append(item)

    _add(*_ww2_assets(text))

    if primary_asset == "animated_map":
        _add("animated_map", "europe_map", "old_map")
    elif primary_asset == "documentary_image":
        _add("documentary_image", "historical_photo", "military_documents")
    elif primary_asset == "archive_video":
        _add("archive_video", "ww2_archive_video")

    if visual_type == "investigation":
        _add("documentary_image", "military_documents")

    # generated_visual só como último recurso — nunca primário
    if not assets:
        _add("archive_video", "documentary_image", "generated_visual")
    else:
        _add("generated_visual")

    return assets


def _resolve_duration(scene: dict, explicit: Optional[float] = None) -> float:
    if explicit and explicit > 0:
        return round(float(explicit), 2)

    for key in ("duration_seconds", "duration_hint", "real_duration"):
        value = scene.get(key)
        if value and float(value) > 0:
            return round(float(value), 2)

    tempo = scene.get("tempo", "")
    if "-" in tempo:
        try:
            start, end = tempo.split("-", 1)
            return round(max(2.0, float(end) - float(start)), 2)
        except ValueError:
            pass

    word_count = len(scene.get("narracao", scene.get("text", "")).split())
    if word_count > 0:
        return round(max(3.0, word_count / 2.5), 2)

    return _DEFAULT_DURATION


def direct_scene_visual(
    scene: dict,
    duration: Optional[float] = None,
) -> VisualDirection:
    """
    Decide estratégia visual para uma cena.

    Exemplo de entrada:
        {"narracao": "Em 1941, a Alemanha iniciou a Operação Barbarossa.", "tipo": "desenvolvimento_1"}
    """

    text = (
        scene.get("narracao")
        or scene.get("text")
        or scene.get("visual", "")
    ).strip()

    normalized = _normalize(text)
    emotion = _resolve_emotion(scene, normalized)
    visual_type, primary_asset, animation_strategy = _resolve_visual_type(normalized, scene)
    assets_needed = _build_assets_needed(normalized, primary_asset, visual_type)
    resolved_duration = _resolve_duration(scene, duration)

    return VisualDirection(
        visual_type=visual_type,
        emotion=emotion,
        assets_needed=assets_needed,
        animation_strategy=animation_strategy,
        duration=resolved_duration,
        primary_asset=primary_asset,
        scene_text=text[:200],
        section_key=scene.get("tipo", scene.get("section_key", "")),
    )


def direct_scenes_visual(scenes_data: dict) -> list[VisualDirection]:
    """Direciona visualmente todas as cenas de um pacote de cenas."""

    directions: list[VisualDirection] = []
    for scene in scenes_data.get("cenas", []):
        directions.append(direct_scene_visual(scene))
    return directions


def apply_visual_directions(scenes_data: dict) -> dict:
    """Enriquece cada cena com campo `visual_direction` (dict)."""

    result = dict(scenes_data)
    enriched = []

    for scene in result.get("cenas", []):
        item = dict(scene)
        direction = direct_scene_visual(item)
        item["visual_direction"] = direction.to_dict()
        enriched.append(item)

    result["cenas"] = enriched
    result["visual_directions_applied"] = True
    return result
