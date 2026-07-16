"""
Asset Quality Score — ranking de mídia stock por relevância e intenção visual.

Fluxo:
    Resultados → Asset Quality Score → Ranking → Melhor Asset → Pipeline
"""

from __future__ import annotations

import re
from typing import Any, Optional

from scripts.core.visual_intent_engine import VisualIntentSpec, resolve_visual_intent
from scripts.video.media_providers.relevance import (
    MIN_ACCEPTABLE_QUALITY_SCORE,
    MIN_PHOTO_RELEVANCE_SCORE,
    MIN_RELEVANCE_SCORE,
    score_photo,
    score_video,
)

_TEXT_OVERLAY_PATTERNS = re.compile(
    r"\b("
    r"text|subtitle|caption|watermark|logo|banner|"
    r"title[\s_-]?card|lower[\s_-]?third|news[\s_-]?ticker"
    r")\b",
    re.IGNORECASE,
)

_PALETTE_KEYWORDS: dict[str, list[str]] = {
    "cold": ["blue", "winter", "ice", "night", "frost", "arctic"],
    "warm_dramatic": ["sunset", "fire", "golden", "warm", "dramatic"],
    "sepia": ["vintage", "old", "antique", "sepia", "archive", "historical"],
    "high_contrast": ["dramatic", "contrast", "shadow", "silhouette"],
    "desaturated": ["grey", "gray", "muted", "monochrome", "fog"],
    "muted": ["soft", "mist", "haze", "atmospheric", "calm"],
    "modern_cold": ["urban", "modern", "city", "steel", "glass"],
    "neutral": [],
}

_ASSET_TYPE_BOOST: dict[str, dict[str, float]] = {
    "historical_photo": {"wikimedia": 0.3, "pixabay": 0.1},
    "archive_video": {"wikimedia": 0.25, "pixabay": 0.15},
    "engraving": {"wikimedia": 0.35},
    "old_map": {"wikimedia": 0.3},
    "stock_video": {"pexels": 0.2, "pixabay": 0.15},
}

# Momento narrativo -> tags visuais desejadas. Baseia-se na intenção de cada
# ato da história (hook/contexto/desenvolvimento/revelação/encerramento).
# Aplicado apenas como ajuste de peso aditivo.
_NARRATIVE_MOMENT_TAGS: dict[str, list[str]] = {
    "hook": ["close", "macro", "dramatic", "contrast", "impact", "intense"],
    "context": ["aerial", "landscape", "architecture", "establishing", "map", "wide", "environment"],
    "development": ["detail", "process", "hands", "demonstration", "closeup", "work"],
    "reveal": ["drama", "dramatic", "motion", "movement", "tension", "reveal"],
    "impact": ["explosion", "aftermath", "scale", "powerful", "dramatic", "destruction"],
    "closing": ["sky", "horizon", "calm", "contemplative", "atmospheric", "sunset"],
}

# tipo da cena -> momento narrativo canônico
_TIPO_TO_MOMENT: dict[str, str] = {
    "hook": "hook",
    "gancho": "hook",
    "contexto": "context",
    "desenvolvimento": "development",
    "desenvolvimento_1": "development",
    "desenvolvimento_2": "development",
    "demonstracao": "development",
    "teste": "development",
    "revelacao": "reveal",
    "consequencias": "impact",
    "impacto": "impact",
    "encerramento": "closing",
    "beneficio": "closing",
    "resultado": "closing",
    "cta": "closing",
}

# style -> tags coerentes com o estilo do plano
_STYLE_TAGS: dict[str, list[str]] = {
    "cinematic": ["cinematic", "dramatic", "film", "moody"],
    "documentary": ["documentary", "real", "footage", "authentic"],
    "archival": ["archive", "vintage", "historical", "old"],
    "dynamic": ["dynamic", "fast", "action", "energetic"],
    "lifestyle": ["lifestyle", "home", "people", "daily"],
    "product": ["product", "closeup", "macro", "studio"],
}

# câmera resolvida -> tags de enquadramento
_CAMERA_TAGS: dict[str, list[str]] = {
    "zoom_in_center": ["close", "macro", "detail"],
    "zoom_out_center": ["wide", "aerial", "establishing", "landscape"],
    "pan_right": ["pan", "sweeping", "tracking"],
    "pan_left": ["pan", "sweeping", "tracking"],
    "parallax_left": ["wide", "static"],
}


def _item_haystack(item: dict, media_type: str) -> str:
    if media_type == "video":
        return (" ".join(item.get("tags", [])) + " " + item.get("url", "")).lower()
    return (item.get("alt", "") + " " + item.get("url", "")).lower()


def _narrative_moment_score(narrative_moment: str, item: dict, media_type: str) -> float:
    moment = _TIPO_TO_MOMENT.get(narrative_moment, narrative_moment)
    tags = _NARRATIVE_MOMENT_TAGS.get(moment, [])
    if not tags:
        return 0.0
    haystack = _item_haystack(item, media_type)
    matches = sum(1 for tag in tags if tag in haystack)
    return min(0.2, matches * 0.07)


def _style_score(style: str, item: dict, media_type: str) -> float:
    tags = _STYLE_TAGS.get(style, [])
    if not tags:
        return 0.0
    haystack = _item_haystack(item, media_type)
    matches = sum(1 for tag in tags if tag in haystack)
    return min(0.15, matches * 0.07)


def _camera_score(camera: str, item: dict, media_type: str) -> float:
    tags = _CAMERA_TAGS.get(camera, [])
    if not tags:
        return 0.0
    haystack = _item_haystack(item, media_type)
    matches = sum(1 for tag in tags if tag in haystack)
    return min(0.12, matches * 0.06)


def _avoid_penalty(avoid: Optional[list], item: dict, media_type: str) -> float:
    if not avoid:
        return 0.0
    haystack = _item_haystack(item, media_type)
    words = {w for term in avoid for w in str(term).lower().split()}
    matches = sum(1 for w in words if w and w in haystack)
    return min(0.3, matches * 0.1)


def _diversity_penalty(
    item: dict,
    media_type: str,
    provider: str,
    recent_selections: Optional[list],
) -> float:
    """Penaliza semelhança com as cenas anteriores (nunca filtra).

    Compara origem (provider), tipo de mídia, categoria (tags) e enquadramento.
    """

    if not recent_selections:
        return 0.0

    haystack_words = set(_item_haystack(item, media_type).split())
    penalty = 0.0

    for recent in recent_selections:
        if not recent:
            continue
        if provider and recent.get("provider") == provider:
            penalty += 0.05
        if media_type and recent.get("media_type") == media_type:
            penalty += 0.03

        recent_words = set(recent.get("category", []))
        if recent_words and haystack_words:
            overlap = len(recent_words & haystack_words)
            union = len(recent_words | haystack_words)
            if union and (overlap / union) >= 0.4:
                penalty += 0.08

        if recent.get("framing") and recent.get("framing") == _framing_of(item, media_type):
            penalty += 0.05

    return min(0.25, penalty)


def _framing_of(item: dict, media_type: str) -> str:
    """Deriva um rótulo de enquadramento simples a partir das tags do asset."""

    haystack = _item_haystack(item, media_type)
    if any(w in haystack for w in ("close", "macro", "detail")):
        return "close"
    if any(w in haystack for w in ("aerial", "wide", "establishing", "landscape")):
        return "wide"
    if any(w in haystack for w in ("pan", "tracking", "sweeping")):
        return "motion"
    return "medium"


def selection_signature(item: dict, media_type: str, provider: str) -> dict:
    """Assinatura leve de um asset selecionado, para comparação de diversidade."""

    return {
        "provider": provider,
        "media_type": media_type,
        "framing": _framing_of(item, media_type),
        "category": list(set(_item_haystack(item, media_type).split()))[:12],
    }


def _has_text_overlay(item: dict, media_type: str) -> bool:
    if media_type == "video":
        haystack = " ".join(item.get("tags", [])) + " " + item.get("url", "")
    else:
        haystack = item.get("alt", "") + " " + item.get("url", "")
    return bool(_TEXT_OVERLAY_PATTERNS.search(haystack))


def _palette_score(item: dict, media_type: str, palette: str) -> float:
    keywords = _PALETTE_KEYWORDS.get(palette, [])
    if not keywords:
        return 0.0

    if media_type == "video":
        haystack = " ".join(item.get("tags", [])).lower()
    else:
        haystack = (item.get("alt", "") + " " + item.get("url", "")).lower()

    matches = sum(1 for kw in keywords if kw in haystack)
    return min(0.3, matches * 0.1)


def _asset_type_boost(item: dict, spec: VisualIntentSpec, provider: str = "") -> float:
    boost = 0.0
    for priority_type in spec.asset_priority[:2]:
        type_boosts = _ASSET_TYPE_BOOST.get(priority_type, {})
        boost = max(boost, type_boosts.get(provider, 0.0))
    return boost


def _emotion_compatibility(emotion: str, item: dict, media_type: str) -> float:
    emotion_tags = {
        "mystery": ["mystery", "dark", "fog", "ancient", "secret"],
        "impact": ["explosion", "dramatic", "action", "powerful", "intense"],
        "calm": ["peaceful", "calm", "serene", "quiet", "nature"],
        "warning": ["danger", "storm", "warning", "tension", "crisis"],
        "sad": ["sad", "melancholy", "rain", "lonely", "memorial"],
    }
    tags = emotion_tags.get(emotion, [])
    if not tags:
        return 0.0

    if media_type == "video":
        haystack = " ".join(item.get("tags", [])).lower()
    else:
        haystack = (item.get("alt", "") + " " + item.get("url", "")).lower()

    matches = sum(1 for tag in tags if tag in haystack)
    return min(0.25, matches * 0.08)


def score_asset(
    query: str,
    item: dict,
    media_type: str = "video",
    visual_intent: Optional[VisualIntentSpec | dict] = None,
    emotion: str = "calm",
    provider: str = "",
    diversity_penalty: float = 0.0,
    narrative_moment: str = "",
    style: str = "",
    camera: str = "",
    avoid: Optional[list] = None,
    recent_selections: Optional[list] = None,
) -> float:
    """
    Pontuação final de um asset considerando múltiplos critérios.
    Maior = melhor.

    Os fatores story-aware (narrative_moment, style, camera, avoid) e a
    diversidade (recent_selections) são apenas ajustes de peso aditivos e
    nunca eliminam candidatos.
    """

    base = score_video(query, item) if media_type == "video" else score_photo(query, item)
    if base <= 0:
        return 0.0

    score = base

    if _has_text_overlay(item, media_type):
        score -= 0.4

    spec = visual_intent
    if spec and not isinstance(spec, VisualIntentSpec):
        spec = resolve_visual_intent(spec)

    if spec:
        score += _palette_score(item, media_type, spec.color_palette)
        score += _asset_type_boost(item, spec, provider)
        # herda sinais da spec quando não fornecidos explicitamente
        style = style or spec.style
        camera = camera or spec.camera
        if avoid is None:
            avoid = spec.avoid

    score += _emotion_compatibility(emotion, item, media_type)

    # --- Ajustes story-aware (aditivos) ---
    score += _narrative_moment_score(narrative_moment, item, media_type)
    score += _style_score(style, item, media_type)
    score += _camera_score(camera, item, media_type)

    # --- Penalizações complementares (score apenas, sem filtro) ---
    score -= _avoid_penalty(avoid, item, media_type)
    score -= _diversity_penalty(item, media_type, provider, recent_selections)
    score -= diversity_penalty

    width = item.get("width", 0)
    height = item.get("height", 0)
    if width >= 3840 or height >= 2160:
        score += 0.15
    elif width >= 1920 or height >= 1080:
        score += 0.1

    if media_type == "video":
        score += 0.20

    return max(0.0, round(score, 4))


def rank_assets(
    query: str,
    candidates: list[dict],
    media_type: str = "video",
    visual_intent: Optional[VisualIntentSpec | dict] = None,
    emotion: str = "calm",
    provider: str = "",
    used_ids: Optional[set] = None,
    min_score: Optional[float] = None,
    narrative_moment: str = "",
    style: str = "",
    camera: str = "",
    avoid: Optional[list] = None,
    recent_selections: Optional[list] = None,
) -> list[tuple[dict, float]]:
    """Ranqueia candidatos por Asset Quality Score."""

    used = used_ids or set()
    threshold = min_score or (
        MIN_RELEVANCE_SCORE if media_type == "video" else MIN_PHOTO_RELEVANCE_SCORE
    )

    ranked = []
    for item in candidates:
        item_id = item.get("id")
        if item_id and item_id in used:
            continue

        item_score = score_asset(
            query,
            item,
            media_type=media_type,
            visual_intent=visual_intent,
            emotion=emotion,
            provider=provider,
            narrative_moment=narrative_moment,
            style=style,
            camera=camera,
            avoid=avoid,
            recent_selections=recent_selections,
        )

        if item_score >= threshold:
            ranked.append((item, item_score))

    ranked.sort(key=lambda pair: pair[1], reverse=True)
    return ranked


def pick_best_asset(
    query: str,
    candidates: list[dict],
    media_type: str = "video",
    visual_intent: Optional[VisualIntentSpec | dict] = None,
    emotion: str = "calm",
    provider: str = "",
    used_ids: Optional[set] = None,
    narrative_moment: str = "",
    style: str = "",
    camera: str = "",
    avoid: Optional[list] = None,
    recent_selections: Optional[list] = None,
) -> tuple[dict | None, float]:
    """Seleciona o melhor asset disponível."""

    ranked = rank_assets(
        query,
        candidates,
        media_type=media_type,
        visual_intent=visual_intent,
        emotion=emotion,
        provider=provider,
        used_ids=used_ids,
        narrative_moment=narrative_moment,
        style=style,
        camera=camera,
        avoid=avoid,
        recent_selections=recent_selections,
    )

    if not ranked:
        return None, 0.0

    best, score = ranked[0]
    min_acceptable = (
        MIN_ACCEPTABLE_QUALITY_SCORE
        if media_type == "video"
        else MIN_PHOTO_RELEVANCE_SCORE
    )

    if score < min_acceptable:
        return None, score

    return best, score


def pick_ranked_assets(
    query: str,
    candidates: list[dict],
    media_type: str = "video",
    visual_intent: Optional[VisualIntentSpec | dict] = None,
    emotion: str = "calm",
    provider: str = "",
    used_ids: Optional[set] = None,
    limit: int = 8,
    narrative_moment: str = "",
    style: str = "",
    camera: str = "",
    avoid: Optional[list] = None,
    recent_selections: Optional[list] = None,
) -> list[dict]:
    """Retorna top N assets ranqueados."""

    ranked = rank_assets(
        query,
        candidates,
        media_type=media_type,
        visual_intent=visual_intent,
        emotion=emotion,
        provider=provider,
        used_ids=used_ids,
        narrative_moment=narrative_moment,
        style=style,
        camera=camera,
        avoid=avoid,
        recent_selections=recent_selections,
    )
    return [item for item, _ in ranked[:limit]]
