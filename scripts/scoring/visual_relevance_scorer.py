"""
Visual Relevance Scorer — ranking heurístico de candidatos por cena.

Score determinístico cacheado por (asset_id, scene_hash).
Sem chamadas de API: keyword match entre a cena e filename/tags/description do asset.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Optional

from scripts.utils.ai_cache import load_cache, save_cache

HARD_PENALTY = 40
MIN_VIDEO_WIDTH = 1920
MIN_VIDEO_HEIGHT = 1080
MIN_PHOTO_WIDTH = 1600
TOP_CANDIDATES = int(__import__("os").getenv("VISUAL_SCORE_TOP_N", "2"))
FALLBACK_KEEP = 3


def scene_hash(scene: dict) -> str:
    phrase = (
        scene.get("narracao")
        or scene.get("visual")
        or scene.get("must_show")
        or ""
    )
    tipo = scene.get("tipo") or scene.get("scene_type") or ""
    raw = f"{tipo}|{phrase}".strip()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def asset_cache_key(item: dict, media_type: str, provider: str) -> str:
    item_id = item.get("id") or item.get("pageURL") or hash(str(item))
    return f"{provider}_{media_type}_{item_id}"


def scene_phrase(scene: dict, *, topic: str = "") -> str:
    parts = [
        scene.get("narracao", ""),
        scene.get("must_show", ""),
        scene.get("visual", ""),
        topic,
    ]
    text = " ".join(p for p in parts if p).strip()
    return text[:500] or topic[:500] or "documentary scene"


def _resolution_penalty(item: dict, media_type: str) -> tuple[int, list[str]]:
    width = int(item.get("width", 0) or 0)
    height = int(item.get("height", 0) or 0)
    reasons: list[str] = []

    if media_type in ("photo", "image"):
        if width > 0 and width < MIN_PHOTO_WIDTH:
            return HARD_PENALTY, ["low_resolution_photo"]
        return 0, reasons

    if width > 0 and height > 0:
        if width < MIN_VIDEO_WIDTH or height < MIN_VIDEO_HEIGHT:
            return HARD_PENALTY, ["low_resolution_video"]
    return 0, reasons


def compute_final_score(scores: dict, metadata_penalty: int = 0) -> float:
    conceptual = float(scores.get("conceptual_match", 0))
    literal = float(scores.get("literal_match", 0))
    quality = float(scores.get("visual_quality", 0))
    on_brand = float(scores.get("on_brand_documentary", 0))
    final = 0.4 * conceptual + 0.25 * literal + 0.2 * quality + 0.15 * on_brand

    ai_penalties = scores.get("hard_penalty_reasons") or []
    final -= HARD_PENALTY * len(ai_penalties)
    final -= metadata_penalty
    return max(0.0, min(100.0, final))


def _asset_search_text(item: dict) -> str:
    tags = item.get("tags", [])
    if isinstance(tags, list):
        tags_text = " ".join(str(t) for t in tags)
    else:
        tags_text = str(tags or "")

    parts = [
        tags_text,
        item.get("alt", ""),
        item.get("description", ""),
        item.get("title", ""),
        item.get("url", ""),
        item.get("pageURL", ""),
        item.get("page_url", ""),
        item.get("credit", ""),
        item.get("photographer", ""),
    ]
    user = item.get("user")
    if isinstance(user, dict):
        parts.append(user.get("name", ""))

    return " ".join(str(p) for p in parts if p).lower()


def _scene_keywords(scene_text: str) -> list[str]:
    words = re.findall(r"[a-zà-ú0-9]{3,}", scene_text.lower())
    seen: set[str] = set()
    keywords: list[str] = []
    for word in words:
        if word not in seen:
            seen.add(word)
            keywords.append(word)
    return keywords


def _heuristic_score(
    scene_text: str,
    item: dict,
    *,
    orchestrator_score: float = 0.0,
    metadata_penalty: int = 0,
    reason: str = "keyword heuristic",
) -> dict:
    haystack = _asset_search_text(item)
    keywords = _scene_keywords(scene_text)
    overlap = sum(1 for word in keywords if word in haystack)

    base = max(orchestrator_score * 100, 35.0)
    literal = min(100.0, base + overlap * 8)
    conceptual = min(100.0, base + overlap * 6)
    quality = min(100.0, 50 + (int(item.get("width", 0) or 0) / 40))
    on_brand = min(100.0, base * 0.8 + overlap * 4)

    scores = {
        "relevance": min(100.0, (literal + conceptual) / 2),
        "literal_match": literal,
        "conceptual_match": conceptual,
        "visual_quality": quality,
        "on_brand_documentary": on_brand,
        "hard_penalty_reasons": [],
        "reason": reason,
        "keyword_overlap": overlap,
    }
    scores["final_score"] = compute_final_score(scores, metadata_penalty)
    return scores


def score_candidate(
    scene: dict,
    item: dict,
    *,
    media_type: str = "video",
    provider: str = "pexels",
    topic: str = "",
    orchestrator_score: float = 0.0,
    use_cache: bool = True,
) -> dict:
    """Pontua um candidato. Retorna dict com final_score e breakdown."""

    phrase = scene_phrase(scene, topic=topic)
    cache_name = f"{asset_cache_key(item, media_type, provider)}_{scene_hash(scene)}"

    if use_cache:
        cached = load_cache("visual_score", cache_name, prefix="vs")
        if cached and "final_score" in cached:
            return cached

    meta_penalty, meta_reasons = _resolution_penalty(item, media_type)
    scores = _heuristic_score(
        phrase,
        item,
        orchestrator_score=orchestrator_score,
        metadata_penalty=meta_penalty,
    )

    if meta_reasons:
        existing = scores.get("hard_penalty_reasons") or []
        scores["hard_penalty_reasons"] = list(set(existing + meta_reasons))
        scores["final_score"] = compute_final_score(scores, meta_penalty)

    scores["asset_id"] = asset_cache_key(item, media_type, provider)
    scores["scene_hash"] = scene_hash(scene)
    scores["provider"] = provider
    scores["media_type"] = media_type
    scores["cached"] = False

    if use_cache:
        scores["cached"] = True
        save_cache("visual_score", cache_name, scores, prefix="vs")

    return scores


def rank_candidates_with_visual_score(
    candidates: list[dict],
    scene: dict,
    *,
    topic: str = "",
    limit: int = TOP_CANDIDATES,
    use_cache: bool = True,
) -> list[dict]:
    """Ranqueia candidatos do orchestrator com Visual Relevance Scorer."""

    scored: list[dict] = []
    for candidate in candidates[:limit]:
        item = candidate.get("item", {})
        provider = candidate.get("provider", "unknown")
        media_type = candidate.get("media_type", "video")
        orch_score = float(candidate.get("score", 0.0))

        breakdown = score_candidate(
            scene,
            item,
            media_type=media_type,
            provider=provider,
            topic=topic,
            orchestrator_score=orch_score,
            use_cache=use_cache,
        )

        enriched = dict(candidate)
        enriched["visual_score"] = breakdown.get("final_score", 0.0)
        enriched["visual_breakdown"] = breakdown
        scored.append(enriched)

    scored.sort(
        key=lambda c: (
            c.get("visual_score", 0.0),
            c.get("score", 0.0),
        ),
        reverse=True,
    )
    return scored
