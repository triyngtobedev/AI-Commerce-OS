"""
Geração de assets de identidade visual do canal YouTube Dark.

Produz foto de perfil e banner otimizados para as especificações da plataforma.
"""

import math
from pathlib import Path
from typing import Tuple

from scripts.core.brand_profile import (
    BRAND_ASSETS,
    YOUTUBE_DARK_BRAND,
    get_brand,
    resolve_font,
    BrandProfile,
)


PROFILE_SIZE = 800
BANNER_WIDTH = 2560
BANNER_HEIGHT = 1440
BANNER_SAFE_WIDTH = 1546
BANNER_SAFE_HEIGHT = 423


def _rgb_to_hex(color: Tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*color)


def _draw_compass_symbol(
    draw,
    center: Tuple[int, int],
    radius: int,
    brand: BrandProfile,
    line_width: int = 3,
):
    """Desenha símbolo de bússola/globo — marca visual do Projeto Atlas."""

    cx, cy = center
    gold = brand.accent_color
    white = brand.text_color

    draw.ellipse(
        [
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
        ],
        outline=gold,
        width=line_width,
    )

    inner = int(radius * 0.72)
    draw.ellipse(
        [
            cx - inner,
            cy - inner,
            cx + inner,
            cy + inner,
        ],
        outline=(*gold[:2], max(0, gold[2] - 40)),
        width=max(1, line_width - 1),
    )

    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x1 = cx + int(inner * 0.3 * math.cos(rad))
        y1 = cy + int(inner * 0.3 * math.sin(rad))
        x2 = cx + int(radius * 0.92 * math.cos(rad))
        y2 = cy + int(radius * 0.92 * math.sin(rad))
        draw.line([(x1, y1), (x2, y2)], fill=gold, width=max(1, line_width - 1))

    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        dot_r = 3 if angle % 90 == 0 else 2
        dx = cx + int(radius * 1.08 * math.cos(rad))
        dy = cy + int(radius * 1.08 * math.sin(rad))
        draw.ellipse(
            [dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r],
            fill=gold,
        )

    font_size = int(radius * 1.1)
    font = resolve_font(brand.font_bold, font_size)
    letter = "A"
    bbox = draw.textbbox((0, 0), letter, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    tx = cx - text_w // 2
    ty = cy - text_h // 2 - bbox[1]
    draw.text((tx + 2, ty + 2), letter, fill=(0, 0, 0), font=font)
    draw.text((tx, ty), letter, fill=white, font=font)


def _radial_gradient_background(size: Tuple[int, int], brand: BrandProfile):
    """Fundo com gradiente radial escuro."""

    from PIL import Image

    width, height = size
    img = Image.new("RGB", size, brand.background_color)
    pixels = img.load()
    cx, cy = width // 2, height // 2
    max_dist = math.sqrt(cx ** 2 + cy ** 2)

    primary = brand.primary_color
    bg = brand.background_color

    for y in range(height):
        for x in range(width):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max_dist
            factor = min(1.0, dist * 1.2)
            r = int(bg[0] + (primary[0] - bg[0]) * factor)
            g = int(bg[1] + (primary[1] - bg[1]) * factor)
            b = int(bg[2] + (primary[2] - bg[2]) * factor)
            pixels[x, y] = (r, g, b)

    return img


def generate_profile_picture(
    output_path: Path,
    brand: BrandProfile = None,
) -> Path:
    """
    Gera foto de perfil 800×800 otimizada para exibição circular.

    Elementos centralizados na área segura (80% do diâmetro).
    """

    from PIL import ImageDraw

    brand = brand or get_brand()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = _radial_gradient_background((PROFILE_SIZE, PROFILE_SIZE), brand)
    draw = ImageDraw.Draw(img)

    safe_radius = int(PROFILE_SIZE * 0.38)
    _draw_compass_symbol(
        draw,
        center=(PROFILE_SIZE // 2, PROFILE_SIZE // 2),
        radius=safe_radius,
        brand=brand,
        line_width=4,
    )

    accent = brand.accent_color
    draw.arc(
        [
            PROFILE_SIZE // 2 - safe_radius - 18,
            PROFILE_SIZE // 2 - safe_radius - 18,
            PROFILE_SIZE // 2 + safe_radius + 18,
            PROFILE_SIZE // 2 + safe_radius + 18,
        ],
        start=200,
        end=340,
        fill=accent,
        width=2,
    )

    img.save(output_path, "PNG", optimize=True)
    return output_path


def generate_banner(
    output_path: Path,
    brand: BrandProfile = None,
    include_safe_zone_guide: bool = False,
) -> Path:
    """
    Gera banner 2560×1440 com conteúdo principal na área segura central.

    Área segura: 1546×423 px centralizada (visível em TV, desktop e mobile).
    """

    from PIL import Image, ImageDraw

    brand = brand or get_brand()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (BANNER_WIDTH, BANNER_HEIGHT), brand.background_color)
    draw = ImageDraw.Draw(img)

    for x in range(0, BANNER_WIDTH, 80):
        alpha = 0.15 if x % 160 == 0 else 0.06
        color = tuple(
            int(brand.primary_color[i] * alpha + brand.background_color[i] * (1 - alpha))
            for i in range(3)
        )
        draw.line([(x, 0), (x, BANNER_HEIGHT)], fill=color, width=1)

    safe_x = (BANNER_WIDTH - BANNER_SAFE_WIDTH) // 2
    safe_y = (BANNER_HEIGHT - BANNER_SAFE_HEIGHT) // 2

    accent = brand.accent_color
    draw.rectangle(
        [(0, safe_y), (BANNER_WIDTH, safe_y + 4)],
        fill=accent,
    )
    draw.rectangle(
        [(0, safe_y + BANNER_SAFE_HEIGHT - 4), (BANNER_WIDTH, safe_y + BANNER_SAFE_HEIGHT)],
        fill=accent,
    )

    left_cx = safe_x - 200
    right_cx = safe_x + BANNER_SAFE_WIDTH + 200
    center_y = BANNER_HEIGHT // 2

    if left_cx > 120:
        _draw_compass_symbol(draw, (left_cx, center_y), 90, brand, line_width=2)

    if right_cx < BANNER_WIDTH - 120:
        _draw_compass_symbol(draw, (right_cx, center_y), 90, brand, line_width=2)

    title_font = resolve_font(brand.font_bold, 96)
    tagline_font = resolve_font(brand.font_body, 36)
    value_font = resolve_font(brand.font_body, 28)

    title = brand.channel_name.upper()
    tagline = brand.tagline
    value_prop = "Documentários sobre os eventos que mudaram o mundo"

    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    title_x = (BANNER_WIDTH - title_w) // 2
    title_y = safe_y + 60

    draw.text(
        (title_x + 3, title_y + 3),
        title,
        fill=(0, 0, 0),
        font=title_font,
    )
    draw.text(
        (title_x, title_y),
        title,
        fill=brand.text_color,
        font=title_font,
    )

    tagline_bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
    tagline_w = tagline_bbox[2] - tagline_bbox[0]
    tagline_x = (BANNER_WIDTH - tagline_w) // 2
    tagline_y = title_y + 110

    draw.text(
        (tagline_x, tagline_y),
        tagline,
        fill=accent,
        font=tagline_font,
    )

    value_bbox = draw.textbbox((0, 0), value_prop, font=value_font)
    value_w = value_bbox[2] - value_bbox[0]
    value_x = (BANNER_WIDTH - value_w) // 2
    value_y = tagline_y + 65

    draw.text(
        (value_x, value_y),
        value_prop,
        fill=(180, 185, 195),
        font=value_font,
    )

    cta = "Novos documentários toda semana  ·  Inscreva-se"
    cta_font = resolve_font(brand.font_body, 22)
    cta_bbox = draw.textbbox((0, 0), cta, font=cta_font)
    cta_w = cta_bbox[2] - cta_bbox[0]
    cta_x = (BANNER_WIDTH - cta_w) // 2
    cta_y = value_y + 55

    draw.text(
        (cta_x, cta_y),
        cta,
        fill=(140, 145, 155),
        font=cta_font,
    )

    if include_safe_zone_guide:
        draw.rectangle(
            [
                safe_x,
                safe_y,
                safe_x + BANNER_SAFE_WIDTH,
                safe_y + BANNER_SAFE_HEIGHT,
            ],
            outline=(255, 0, 0),
            width=2,
        )

    img.save(output_path, "PNG", optimize=True)
    return output_path


def generate_all_assets(
    output_dir: Path = None,
    brand: BrandProfile = None,
) -> dict:
    """Gera todos os assets de canal e retorna caminhos."""

    brand = brand or get_brand()
    output_dir = output_dir or BRAND_ASSETS

    paths = {
        "profile_picture": generate_profile_picture(
            output_dir / "profile_picture.png",
            brand=brand,
        ),
        "banner": generate_banner(
            output_dir / "banner.png",
            brand=brand,
        ),
        "banner_safe_zone": generate_banner(
            output_dir / "banner_safe_zone_guide.png",
            brand=brand,
            include_safe_zone_guide=True,
        ),
    }

    return paths


if __name__ == "__main__":
    assets = generate_all_assets()
    print("Assets gerados:")
    for name, path in assets.items():
        print(f"  {name}: {path}")
