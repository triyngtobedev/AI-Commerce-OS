"""
Overlays de marca para thumbnails e vídeo.
"""

from pathlib import Path
from typing import Optional

from scripts.core.brand_profile import get_brand, resolve_font, BrandProfile


def _wrap_text(text: str, max_chars: int = 18) -> list:
    words = text.upper().split()
    lines = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()

        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines[:3]


def apply_brand_thumbnail(
    image_path: Path,
    hook_text: str,
    output_path: Path,
    brand: Optional[BrandProfile] = None,
    subtitle: str = "",
) -> bool:
    """
    Aplica layout de thumbnail profissional com hierarquia visual.
    """

    try:
        from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
    except ImportError:
        return False

    brand = brand or get_brand()

    try:
        img = Image.open(image_path).convert("RGB")
        img = img.resize(
            (brand.thumbnail_width, brand.thumbnail_height),
            Image.LANCZOS,
        )

        img = ImageEnhance.Contrast(img).enhance(1.15)
        img = ImageEnhance.Color(img).enhance(1.1)

        overlay = Image.new("RGB", img.size, brand.primary_color)
        img = Image.blend(img, overlay, alpha=0.25)

        draw = ImageDraw.Draw(img)

        accent_bar = Image.new(
            "RGB",
            (brand.thumbnail_width, 12),
            brand.accent_color,
        )
        img.paste(accent_bar, (0, 0))

        hook_font = resolve_font(brand.font_bold, 72)
        sub_font = resolve_font(brand.font_body, 28)
        brand_font = resolve_font(brand.font_body, 22)

        lines = _wrap_text(hook_text)

        y = 180
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=hook_font)
            text_w = bbox[2] - bbox[0]
            x = (brand.thumbnail_width - text_w) // 2

            draw.text(
                (x + 3, y + 3),
                line,
                fill=(0, 0, 0),
                font=hook_font,
            )
            draw.text(
                (x, y),
                line,
                fill=brand.text_color,
                font=hook_font,
            )
            y += 80

        if subtitle:
            draw.text(
                (40, 520),
                subtitle[:60],
                fill=brand.accent_color,
                font=sub_font,
            )

        draw.rectangle(
            [(0, 640), (brand.thumbnail_width, brand.thumbnail_height)],
            fill=brand.background_color,
        )

        draw.text(
            (40, 655),
            brand.channel_name.upper(),
            fill=brand.accent_color,
            font=brand_font,
        )

        draw.text(
            (brand.thumbnail_width - 280, 655),
            brand.tagline,
            fill=(180, 180, 180),
            font=brand_font,
        )

        vignette = Image.new("L", img.size, 0)
        vig_draw = ImageDraw.Draw(vignette)
        vig_draw.ellipse(
            [
                -100, -50,
                brand.thumbnail_width + 100,
                brand.thumbnail_height + 100,
            ],
            fill=200,
        )
        vignette = vignette.filter(ImageFilter.GaussianBlur(80))
        img = Image.composite(img, Image.new("RGB", img.size, (0, 0, 0)), vignette)

        img.save(output_path, "JPEG", quality=92)
        return True

    except Exception as error:
        print(f"⚠️ Erro no brand thumbnail: {error}")
        return False


def watermark_filter(brand: Optional[BrandProfile] = None) -> str:
    """Retorna filtro FFmpeg drawtext para marca d'água discreta."""

    brand = brand or get_brand()
    text = brand.channel_name.replace("'", "\\'")

    return (
        f"drawtext=text='{text}':"
        f"fontcolor=white@{brand.watermark_opacity}:"
        "fontsize=18:"
        "x=w-tw-30:y=h-th-20:"
        "box=1:boxcolor=black@0.2:boxborderw=6"
    )
