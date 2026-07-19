"""
Thumbnail Scorer — estima CTR e legibilidade de variações de thumbnail.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from scripts.utils.json_parser import safe_parse_json

THUMBNAIL_SCORE_MODEL = os.getenv("VISUAL_SCORE_MODEL", "gemini-2.5-flash")
MIN_TEXT_LEGIBILITY = 70

_SCORE_PROMPT = """Avalie esta thumbnail para YouTube dark documentário.

Título do vídeo: "{title}"
Variação: {variant} — {concept}

Retorne APENAS JSON:
{{
  "ctr_estimate": 0-100,
  "clarity": 0-100,
  "curiosity_gap": 0-100,
  "text_legibility": 0-100,
  "reason": "1 frase"
}}"""


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
        "reason": "heuristic contrast score",
    }


def _call_gemini_score(
    image_path: Path,
    *,
    title: str,
    variant: str,
    concept: str,
) -> Optional[dict]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        mime = "image/jpeg"
        if image_path.suffix.lower() == ".png":
            mime = "image/png"

        prompt = _SCORE_PROMPT.format(
            title=title[:120],
            variant=variant,
            concept=concept[:120],
        )

        response = client.models.generate_content(
            model=THUMBNAIL_SCORE_MODEL,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(
                            data=image_path.read_bytes(),
                            mime_type=mime,
                        ),
                    ],
                )
            ],
        )
        parsed = safe_parse_json(response.text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return None

    return None


def score_thumbnail(
    image_path: Path,
    *,
    title: str = "",
    variant: str = "A",
    concept: str = "",
) -> dict:
    """Pontua uma thumbnail. Retorna breakdown + composite score."""

    scores = _call_gemini_score(
        image_path,
        title=title,
        variant=variant,
        concept=concept,
    )
    if not scores:
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
