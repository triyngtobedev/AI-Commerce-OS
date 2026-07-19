"""
Visual Relevance Scorer — avaliação multimodal de candidatos por cena.

Score determinístico cacheado por (asset_id, scene_hash).
Modelo padrão: gemini-2.0-flash-lite (multimodal, free tier).
Gemini atua como desempate/editor final sobre candidatos pré-filtrados pelo orchestrator.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from scripts.ai.gemini_quota import (
    handle_gemini_error,
    is_gemini_quota_exhausted,
    record_gemini_call,
)
from scripts.utils.ai_cache import load_cache, save_cache
from scripts.utils.json_parser import safe_parse_json
from scripts.video.media_downloader import download_file, select_photo_url

VISUAL_SCORE_MODEL = os.getenv("VISUAL_SCORE_MODEL", "gemini-2.0-flash-lite")
HARD_PENALTY = 40
MIN_VIDEO_WIDTH = 1920
MIN_VIDEO_HEIGHT = 1080
MIN_PHOTO_WIDTH = 1600
TOP_CANDIDATES = int(os.getenv("VISUAL_SCORE_TOP_N", "2"))
FALLBACK_KEEP = 3

_SCORE_PROMPT = """Avalie a relevância visual deste asset para a cena documentária.

Frase da cena: "{scene_phrase}"
Tipo de mídia: {media_type}

Penalize HARD (-40 cada, inclua em hard_penalty_reasons):
- pessoa olhando para câmera sorrindo (stock genérico)
- watermark visível
- baixa resolução perceptível

Retorne APENAS JSON estrito:
{{
  "relevance": 0-100,
  "literal_match": 0-100,
  "conceptual_match": 0-100,
  "visual_quality": 0-100,
  "on_brand_documentary": 0-100,
  "hard_penalty_reasons": [],
  "reason": "1 frase"
}}"""


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


def preview_url(item: dict, media_type: str) -> Optional[str]:
    if media_type in ("photo", "image"):
        return select_photo_url(item)

    image = item.get("image")
    if image:
        return image

    pictures = item.get("video_pictures") or []
    if pictures:
        first = pictures[0]
        if isinstance(first, dict):
            return first.get("picture") or first.get("nr")
        if isinstance(first, str):
            return first

    return select_photo_url(item)


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


def _heuristic_score(
    scene_text: str,
    item: dict,
    *,
    orchestrator_score: float = 0.0,
    metadata_penalty: int = 0,
    reason: str = "heuristic fallback (sem Gemini)",
) -> dict:
    tags = " ".join(item.get("tags", [])).lower()
    text = scene_text.lower()
    overlap = sum(1 for word in text.split() if len(word) > 4 and word in tags)
    base = max(orchestrator_score * 100, 40.0) + overlap * 5
    scores = {
        "relevance": min(100.0, base),
        "literal_match": min(100.0, base * 0.9),
        "conceptual_match": min(100.0, base * 0.85),
        "visual_quality": min(100.0, 50 + (item.get("width", 0) / 40)),
        "on_brand_documentary": min(100.0, base * 0.8),
        "hard_penalty_reasons": [],
        "reason": reason,
    }
    scores["final_score"] = compute_final_score(scores, metadata_penalty)
    return scores


def _call_gemini_multimodal(
    scene_text: str,
    image_path: Path,
    *,
    media_type: str,
) -> Optional[dict]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    if is_gemini_quota_exhausted():
        record_gemini_call(
            stage="visual_score",
            model=VISUAL_SCORE_MODEL,
            fallback=True,
        )
        print("[Visual Score] Quota Gemini esgotada — heuristic fallback")
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        image_bytes = image_path.read_bytes()
        mime = "image/jpeg"
        if image_path.suffix.lower() == ".png":
            mime = "image/png"

        prompt = _SCORE_PROMPT.format(
            scene_phrase=scene_text[:400],
            media_type=media_type,
        )

        response = client.models.generate_content(
            model=VISUAL_SCORE_MODEL,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(data=image_bytes, mime_type=mime),
                    ],
                )
            ],
        )
        record_gemini_call(stage="visual_score", model=VISUAL_SCORE_MODEL)
        parsed = safe_parse_json(response.text)
        if isinstance(parsed, dict):
            return parsed
    except Exception as error:
        handle_gemini_error(error, stage="visual_score")
        return None

    return None


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
    url = preview_url(item, media_type)

    scores: Optional[dict] = None
    fallback_reason = "heuristic fallback (sem Gemini)"
    if is_gemini_quota_exhausted():
        fallback_reason = "heuristic fallback (quota Gemini esgotada)"

    if url and not is_gemini_quota_exhausted():
        with tempfile.TemporaryDirectory() as tmp:
            preview_path = Path(tmp) / "preview.jpg"
            if _download_preview(url, preview_path):
                scores = _call_gemini_multimodal(
                    phrase, preview_path, media_type=media_type,
                )

    if not scores:
        scores = _heuristic_score(
            phrase,
            item,
            orchestrator_score=orchestrator_score,
            metadata_penalty=meta_penalty,
            reason=fallback_reason,
        )
    else:
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


def _download_preview(url: str, dest: Path) -> bool:
    try:
        download_file(url, dest, timeout=20)
        return dest.exists() and dest.stat().st_size > 1024
    except Exception:
        return False


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
