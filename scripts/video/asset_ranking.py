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
) -> float:
    """
    Pontuação final de um asset considerando múltiplos critérios.
    Maior = melhor.
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

    score += _emotion_compatibility(emotion, item, media_type)
    score -= diversity_penalty

    width = item.get("width", 0)
    height = item.get("height", 0)
    if width >= 3840 or height >= 2160:
        score += 0.15
    elif width >= 1920 or height >= 1080:
        score += 0.1

    if media_type == "video":
        score += 0.12

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

        penalty = 0.15 if item_id and item_id in used else 0.0
        item_score = score_asset(
            query,
            item,
            media_type=media_type,
            visual_intent=visual_intent,
            emotion=emotion,
            provider=provider,
            diversity_penalty=penalty,
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
    )
    return [item for item, _ in ranked[:limit]]
