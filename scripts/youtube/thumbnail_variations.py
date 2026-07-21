"""
Thumbnail Variations — gera 3 variações A/B/C a partir de thumbnail_brief.json.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from scripts.core.brand_kit import get_brand_kit
from scripts.youtube.thumbnail_scorer import MIN_TEXT_LEGIBILITY, score_thumbnail
from scripts.youtube.thumbnail_generator import (
    _pick_best_hero_image,
    _derive_hook_text,
    _extract_frame,
    _video_frame_timestamp,
)
from scripts.video.scene_timeline import extract_scenes, is_image

THUMBNAIL_IMAGE_MODEL = os.getenv(
    "THUMBNAIL_IMAGE_MODEL",
    "gemini-2.5-flash-image",
)

VARIANT_SPECS = {
    "A": {
        "concept": "Rosto + choque",
        "prompt_suffix": (
            "Central subject with strong expression (surprise or tension), "
            "3-5 word bold text overlay, high contrast, dark documentary YouTube thumbnail, "
            "1280x720, no generic stock smile at camera"
        ),
    },
    "B": {
        "concept": "Objeto + número",
        "prompt_suffix": (
            "Central object or product with large prominent number or statistic, "
            "minimal text, high contrast dark documentary style, 1280x720"
        ),
    },
    "C": {
        "concept": "Antes/Depois ou vs",
        "prompt_suffix": (
            "Split visual before/after or versus composition, two conflicting elements, "
            "dark documentary YouTube thumbnail, high contrast, 1280x720"
        ),
    },
}


def load_thumbnail_brief(output_dir: Path) -> Optional[dict]:
    path = output_dir / "thumbnail_brief.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _build_variant_prompt(
    brief: dict,
    variant: str,
    hook_text: str,
    topic: str,
) -> str:
    spec = VARIANT_SPECS[variant]
    recommended = brief.get("recommended") or {}
    subject = recommended.get("subject") or brief.get("topic") or topic
    mood = recommended.get("mood") or "dark dramatic high contrast"
    text = hook_text[:40] if variant == "A" else ""

    return (
        f"YouTube dark documentary thumbnail. Topic: {topic}. "
        f"Subject: {subject}. Mood: {mood}. "
        f"Text overlay (if any): '{text}'. "
        f"{spec['prompt_suffix']}"
    )


def _generate_with_gemini_image(prompt: str, output_path: Path) -> bool:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return False

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=THUMBNAIL_IMAGE_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(part.inline_data.data)
                return output_path.exists() and output_path.stat().st_size > 2048
    except Exception:
        return False

    return False


def _compose_variant_from_hero(
    hero: Path,
    hook_text: str,
    output_path: Path,
    *,
    kit,
    topic: str,
    variant: str,
) -> bool:
    texts = {
        "A": hook_text[:35],
        "B": hook_text.split()[0][:8] if hook_text else topic[:8],
        "C": "VS",
    }
    overlay = texts.get(variant, hook_text[:30])
    return kit.compose_thumbnail(hero, overlay, output_path, topic=topic)


def generate_thumbnail_variations(
    output_dir: Path,
    *,
    subject: dict,
    content: dict,
    strategy: Optional[dict] = None,
    scenes: Optional[dict] = None,
    video_path: Optional[str] = None,
    platform: str = "youtube_dark",
) -> dict:
    """
    Gera 3 variações, pontua e escolhe vencedora.
    Retorna metadata com paths e scores.
    """

    output_dir = Path(output_dir)
    brief = load_thumbnail_brief(output_dir)
    if not brief:
        from scripts.youtube.youtube_packager import generate_thumbnail_brief

        brief = generate_thumbnail_brief(
            subject.get("nome", content.get("titulo", "")),
            content,
            script=None,
            scenes=scenes,
            strategy=strategy,
        )
        (output_dir / "thumbnail_brief.json").write_text(
            json.dumps(brief, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    roteiro_template = (strategy or {}).get("roteiro_template", "")
    kit = get_brand_kit(platform, roteiro_template=roteiro_template)
    hook_text = _derive_hook_text(content, strategy)
    topic = subject.get("nome", content.get("titulo", ""))[:80]
    title = content.get("titulo", topic)

    hero = _pick_best_hero_image(output_dir, scenes, video_path)
    variants_dir = output_dir / "assets" / "thumbnail_variants"
    variants_dir.mkdir(parents=True, exist_ok=True)

    scored: list[dict] = []

    for variant in ("A", "B", "C"):
        spec = VARIANT_SPECS[variant]
        out_path = variants_dir / f"thumb_{variant.lower()}.jpg"
        prompt = _build_variant_prompt(brief, variant, hook_text, topic)

        generated = _generate_with_gemini_image(prompt, out_path)
        if not generated and hero:
            if is_image(hero):
                hero_frame = hero
            else:
                hero_frame = variants_dir / f"hero_{variant.lower()}.jpg"
                if not hero_frame.exists():
                    _extract_frame(hero, hero_frame, _video_frame_timestamp(hero))
                hero_frame = hero_frame if hero_frame.exists() else None

            if hero_frame:
                generated = _compose_variant_from_hero(
                    hero_frame,
                    hook_text,
                    out_path,
                    kit=kit,
                    topic=topic,
                    variant=variant,
                )

        if not generated or not out_path.exists():
            continue

        scores = score_thumbnail(
            out_path,
            title=title,
            variant=variant,
            concept=spec["concept"],
        )

        if (
            scores.get("text_legibility", 100) < MIN_TEXT_LEGIBILITY
            and variant == "A"
        ):
            strict_prompt = prompt + " CRITICAL: maximum 3 words, ultra bold sans-serif, huge text."
            if _generate_with_gemini_image(strict_prompt, out_path):
                scores = score_thumbnail(
                    out_path,
                    title=title,
                    variant=variant,
                    concept=spec["concept"],
                )

        scored.append({
            "variant": variant,
            "concept": spec["concept"],
            "path": str(out_path),
            "scores": scores,
        })

    if not scored:
        return {"winner": None, "variants": [], "runners_up": []}

    ranked = sorted(
        scored,
        key=lambda v: v["scores"].get("composite_score", 0),
        reverse=True,
    )
    winner = ranked[0]
    runners_up = ranked[1:]

    winner_path = Path(winner["path"])
    final_path = output_dir / "thumbnail.jpg"
    if winner_path.exists():
        final_path.write_bytes(winner_path.read_bytes())

    report = {
        "winner": winner,
        "runners_up": runners_up,
        "variants": scored,
        "final_thumbnail": str(final_path) if final_path.exists() else None,
    }

    (output_dir / "thumbnail_ab_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return report
