"""
Thumbnail Scorer — estima CTR e legibilidade de variações de thumbnail.

Thumbnail scoring disabled — Gemini removed.
SPRINT30_THUMBNAIL_AB=false (default) skips this path; heuristic contrast only when called.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

MIN_TEXT_LEGIBILITY = 70


def _heuristic_score(path: Path, *, variant: str) -> dict:
    from scripts.core.brand_kit import score_image_contrast

    contrast = score_image_contrast(path)
    base = min(100.0, contrast * 2.5)
    variant_boost = {"A": 8, "B": 6, "C": 5}.get(variant, 0)
    return {
        "ctr_estimate": min(100.0, base + variant_boost),
        "clarity": min(100.0, base),
        "curiosity_gap": min(100.0, base * 0.85 + variant_boost),
        "text_legibility": min(100.0, 55 + variant_boost * 3),
        "reason": "heuristic contrast score (Gemini removed)",
    }


def score_thumbnail(
    image_path: Path,
    *,
    title: str = "",
    variant: str = "A",
    concept: str = "",
) -> dict:
    """Pontua uma thumbnail. Retorna breakdown + composite score."""

    scores = _heuristic_score(image_path, variant=variant)

    composite = (
        float(scores.get("ctr_estimate", 0)) * 0.35
        + float(scores.get("clarity", 0)) * 0.20
        + float(scores.get("curiosity_gap", 0)) * 0.25
        + float(scores.get("text_legibility", 0)) * 0.20
    )
    scores["composite_score"] = round(composite, 2)
    scores["variant"] = variant
    return scores


def pick_winner(
    scored_variants: list[dict],
) -> tuple[dict, list[dict]]:
    """Escolhe vencedora e retorna (winner, runners_up)."""

    if not scored_variants:
        raise ValueError("Nenhuma variação para pontuar")

    ranked = sorted(
        scored_variants,
        key=lambda v: v.get("scores", {}).get("composite_score", 0),
        reverse=True,
    )
    winner = ranked[0]
    runners = ranked[1:]
    return winner, runners
