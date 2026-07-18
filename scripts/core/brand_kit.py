"""
BrandKit — identidade visual reutilizável para YouTube Dark.

Centraliza paleta, tipografia, templates de thumbnail, cards de abertura/
encerramento, lower thirds, overlays e presets cinematográficos por tipo de cena.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple

from scripts.core.brand_profile import BrandProfile, get_brand, resolve_font


@dataclass(frozen=True)
class ColorPalette:
    background: Tuple[int, int, int]
    primary: Tuple[int, int, int]
    accent: Tuple[int, int, int]
    text: Tuple[int, int, int]
    text_muted: Tuple[int, int, int] = (180, 185, 195)
    shadow: Tuple[int, int, int] = (0, 0, 0)
    panel: Tuple[int, int, int] = (8, 12, 24)


@dataclass(frozen=True)
class Typography:
    title_size: int = 96
    hook_size: int = 88
    subtitle_size: int = 32
    body_size: int = 24
    badge_size: int = 20
    lower_third_size: int = 28


@dataclass(frozen=True)
class ThumbnailStyle:
    width: int = 1280
    height: int = 720
    text_panel_ratio: float = 0.42
    hook_max_words: int = 4
    hook_max_lines: int = 2
    hook_max_chars_per_line: int = 14
    contrast_boost: float = 1.35
    saturation_boost: float = 1.22
    overlay_blend: float = 0.18
    accent_bar_height: int = 6


@dataclass(frozen=True)
class VideoOverlayStyle:
    intro_seconds: float = 2.0
    outro_seconds: float = 2.5
    lower_third_seconds: float = 4.0
    watermark_opacity: float = 0.12
    show_lower_third_on: tuple = ("hook", "revelacao")


@dataclass(frozen=True)
class CinematicStyle:
    transition_seconds: float = 0.7
    crossfade_seconds: float = 0.45
    ken_burns_zoom_max: float = 1.22
    color_grade: str = "eq=contrast=1.08:brightness=-0.03:saturation=1.08"
    vignette: str = "vignette=PI/4.5"
    opening_fade_seconds: float = 0.8
    closing_fade_seconds: float = 2.0
    scene_fade_seconds: float = 0.5


SCENE_MOTION: dict[str, str] = {
    "hook": "zoom_in_center",
    "contexto": "parallax_right",
    "desenvolvimento_1": "parallax_left",
    "desenvolvimento_2": "drift_up",
    "revelacao": "zoom_in_center",
    "consequencias": "parallax_right",
    "impacto": "pan_left",
    "encerramento": "zoom_out_center",
}

SCENE_CROSSFADE: dict[str, float] = {
    "hook": 0.35,
    "revelacao": 0.55,
    "encerramento": 0.6,
}


@dataclass
class BrandKit:
    profile: BrandProfile
    colors: ColorPalette
    typography: Typography = field(default_factory=Typography)
    thumbnail: ThumbnailStyle = field(default_factory=ThumbnailStyle)
    overlay: VideoOverlayStyle = field(default_factory=VideoOverlayStyle)
    cinematic: CinematicStyle = field(default_factory=CinematicStyle)

    @classmethod
    def from_profile(cls, profile: BrandProfile) -> "BrandKit":
        return cls(
            profile=profile,
            colors=ColorPalette(
                background=profile.background_color,
                primary=profile.primary_color,
                accent=profile.accent_color,
                text=profile.text_color,
            ),
        )

    def motion_for_scene(self, scene_type: str, scene_index: int = 0) -> str:
        if scene_type in SCENE_MOTION:
            return SCENE_MOTION[scene_type]
        presets = [
            "zoom_in_center", "parallax_left", "parallax_right",
            "drift_up", "drift_down", "pan_left", "zoom_out_center",
        ]
        return presets[scene_index % len(presets)]

    def crossfade_for_scene(self, scene_type: str) -> float:
        return SCENE_CROSSFADE.get(scene_type, self.cinematic.crossfade_seconds)

    def should_show_lower_third(self, scene_type: str) -> bool:
        return scene_type in self.overlay.show_lower_third_on

    # ── Elementos gráficos ──────────────────────────────────────────────

    def draw_compass_badge(
        self,
        draw,
        center: Tuple[int, int],
        radius: int,
        line_width: int = 2,
    ):
        """Símbolo de bússola — marca visual do canal."""

        cx, cy = center
        gold = self.colors.accent
        white = self.colors.text

        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            outline=gold,
            width=line_width,
        )

        inner = int(radius * 0.72)
        draw.ellipse(
            [cx - inner, cy - inner, cx + inner, cy + inner],
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

        font = resolve_font(self.profile.font_bold, int(radius * 1.1))
        letter = "A"
        bbox = draw.textbbox((0, 0), letter, font=font)
        tx = cx - (bbox[2] - bbox[0]) // 2
        ty = cy - (bbox[3] - bbox[1]) // 2 - bbox[1]
        draw.text((tx + 2, ty + 2), letter, fill=self.colors.shadow, font=font)
        draw.text((tx, ty), letter, fill=white, font=font)

    def _radial_gradient(self, size: Tuple[int, int]):
        from PIL import Image, ImageDraw

        width, height = size
        img = Image.new("RGB", size, self.colors.background)
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        max_r = int(math.sqrt(cx ** 2 + cy ** 2))

        bg = self.colors.background
        primary = self.colors.primary

        for r in range(max_r, 0, -8):
            factor = min(1.0, (r / max_r) * 1.15)
            color = tuple(
                int(bg[i] + (primary[i] - bg[i]) * factor) for i in range(3)
            )
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

        return img

    # ── Thumbnail ───────────────────────────────────────────────────────

    def render_thumbnail_background(
        self,
        output_path: Path,
        topic: str = "",
    ) -> bool:
        """Gera fundo de thumbnail via gradiente radial (fallback sem hero image)."""

        try:
            from PIL import ImageDraw
        except ImportError:
            return False

        style = self.thumbnail
        img = self._radial_gradient((style.width, style.height))
        draw = ImageDraw.Draw(img)

        draw.rectangle(
            [(0, 0), (style.width, style.accent_bar_height)],
            fill=self.colors.accent,
        )

        self.draw_compass_badge(
            draw,
            (style.width - 80, style.height // 2),
            48,
            line_width=2,
        )

        if topic:
            sub_font = resolve_font(self.profile.font_body, self.typography.subtitle_size)
            draw.text(
                (48, style.height - 100),
                topic[:45].upper(),
                fill=self.colors.text_muted,
                font=sub_font,
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, "JPEG", quality=93)
        return True

    def wrap_hook_text(self, text: str) -> list[str]:
        words = text.upper().strip().split()
        if not words:
            return ["DOCUMENTÁRIO"]

        words = words[: self.thumbnail.hook_max_words]
        lines: list[str] = []
        current = ""

        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) <= self.thumbnail.hook_max_chars_per_line:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        return lines[: self.thumbnail.hook_max_lines]

    def compose_thumbnail(
        self,
        hero_image_path: Path,
        hook_text: str,
        output_path: Path,
        topic: str = "",
    ) -> bool:
        """
        Layout CTR: painel escuro à esquerda com hook grande,
        imagem hero à direita com gradiente de transição.
        """

        try:
            from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
        except ImportError:
            return False

        style = self.thumbnail
        w, h = style.width, style.height

        try:
            hero = Image.open(hero_image_path).convert("RGB")
        except OSError:
            return False

        hero = hero.resize((w, h), Image.LANCZOS)
        hero = ImageEnhance.Contrast(hero).enhance(style.contrast_boost)
        hero = ImageEnhance.Color(hero).enhance(style.saturation_boost)

        panel_w = int(w * style.text_panel_ratio)
        canvas = Image.new("RGB", (w, h), self.colors.panel)
        hero_crop = hero.crop((panel_w, 0, w, h))
        canvas.paste(hero_crop, (panel_w, 0))

        draw = ImageDraw.Draw(canvas)

        blend_w = 80
        blend_x = panel_w - blend_w
        grad_1d = Image.new("L", (blend_w, 1))
        for x in range(blend_w):
            grad_1d.putpixel((x, 0), int(255 * x / max(1, blend_w - 1)))
        gradient = grad_1d.resize((blend_w, h), Image.NEAREST)
        panel_strip = Image.new("RGB", (blend_w, h), self.colors.panel)
        hero_strip = hero.crop((blend_x, 0, panel_w, h))
        canvas.paste(Image.composite(hero_strip, panel_strip, gradient), (blend_x, 0))

        accent_bar = Image.new("RGB", (panel_w, style.accent_bar_height), self.colors.accent)
        canvas.paste(accent_bar, (0, 0))

        typo = self.typography
        hook_font = resolve_font(self.profile.font_bold, typo.hook_size)
        sub_font = resolve_font(self.profile.font_body, typo.subtitle_size)
        badge_font = resolve_font(self.profile.font_body, typo.badge_size)

        lines = self.wrap_hook_text(hook_text)
        y = 140

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=hook_font)
            text_h = bbox[3] - bbox[1]

            for dx, dy in [(4, 4), (3, 3), (2, 2)]:
                draw.text((48 + dx, y + dy), line, fill=self.colors.shadow, font=hook_font)

            draw.text((48, y), line, fill=self.colors.text, font=hook_font)

            accent_y = y + text_h + 8
            draw.rectangle(
                [(48, accent_y), (48 + min(panel_w - 96, len(line) * 22), accent_y + 4)],
                fill=self.colors.accent,
            )
            y += text_h + 36

        if topic:
            draw.text(
                (48, h - 120),
                topic[:45].upper(),
                fill=self.colors.accent,
                font=sub_font,
            )

        self.draw_compass_badge(draw, (panel_w - 60, 60), 28, line_width=2)

        draw.rectangle([(0, h - 56), (w, h)], fill=self.colors.background)
        draw.text(
            (48, h - 44),
            self.profile.channel_name.upper(),
            fill=self.colors.accent,
            font=badge_font,
        )
        draw.text(
            (w - 320, h - 44),
            self.profile.tagline,
            fill=self.colors.text_muted,
            font=badge_font,
        )

        vignette = Image.new("L", (w, h), 0)
        vig_draw = ImageDraw.Draw(vignette)
        vig_draw.ellipse([-60, -30, w + 60, h + 60], fill=210)
        vignette = vignette.filter(ImageFilter.GaussianBlur(60))
        dark = Image.new("RGB", (w, h), (0, 0, 0))
        canvas = Image.composite(canvas, dark, vignette)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path, "JPEG", quality=93)
        return True

    # ── Cards de abertura / encerramento ────────────────────────────────

    def render_intro_card(self, output_path: Path, topic: str = "") -> bool:
        return self._render_branded_card(output_path, "intro", topic)

    def render_outro_card(self, output_path: Path, topic: str = "") -> bool:
        return self._render_branded_card(output_path, "outro", topic)

    def _render_branded_card(
        self,
        output_path: Path,
        card_type: str,
        topic: str,
    ) -> bool:
        try:
            from PIL import ImageDraw
        except ImportError:
            return False

        img = self._radial_gradient((1920, 1080))
        draw = ImageDraw.Draw(img)

        draw.rectangle([(0, 0), (1920, 6)], fill=self.colors.accent)
        draw.rectangle([(0, 1074), (1920, 1080)], fill=self.colors.accent)

        self.draw_compass_badge(draw, (960, 380), 80, line_width=3)

        title_font = resolve_font(self.profile.font_bold, 72)
        sub_font = resolve_font(self.profile.font_body, 36)
        cta_font = resolve_font(self.profile.font_body, 28)

        if card_type == "intro" and topic:
            headline = topic[:60].upper()
        else:
            headline = self.profile.channel_name.upper()

        bbox = draw.textbbox((0, 0), headline, font=title_font)
        tx = (1920 - bbox[2] + bbox[0]) // 2
        draw.text((tx + 3, 503), headline, fill=self.colors.shadow, font=title_font)
        draw.text((tx, 500), headline, fill=self.colors.text, font=title_font)

        tagline = self.profile.tagline
        tbbox = draw.textbbox((0, 0), tagline, font=sub_font)
        ttx = (1920 - tbbox[2] + tbbox[0]) // 2
        draw.text((ttx, 590), tagline, fill=self.colors.accent, font=sub_font)

        if card_type == "outro":
            cta = "Inscreva-se para mais documentários"
            cbbox = draw.textbbox((0, 0), cta, font=cta_font)
            ctx = (1920 - cbbox[2] + cbbox[0]) // 2
            draw.text((ctx, 680), cta, fill=self.colors.text_muted, font=cta_font)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, "JPEG", quality=92)
        return True

    # ── Filtros FFmpeg ──────────────────────────────────────────────────

    def watermark_filter(self) -> str:
        text = self.profile.channel_name.replace("'", "\\'")
        opacity = self.overlay.watermark_opacity
        return (
            f"drawtext=text='{text}':"
            f"fontcolor=white@{opacity:.2f}:"
            "fontsize=13:"
            "x=w-tw-20:y=h-th-14:"
            "box=1:boxcolor=black@0.12:boxborderw=3"
        )

    def lower_third_filter(self, text: str, duration: float) -> str:
        # Apóstrofo vira U+2019 — \' quebra aspas simples do drawtext no FFmpeg
        safe = text.replace("'", "\u2019").replace(":", "\\:")[:50]
        fade = min(0.6, duration * 0.15)
        show = max(0.5, duration - fade * 2)
        accent = self.colors.accent
        r, g, b = accent
        return (
            f"drawtext=text='{safe}':"
            f"fontcolor=0x{r:02x}{g:02x}{b:02x}:"
            "fontsize=26:"
            "x=60:y=h-120:"
            "box=1:boxcolor=0x080818@0.75:boxborderw=8:"
            f"enable='between(t\\,{fade:.2f}\\,{show:.2f})'"
        )


YOUTUBE_DARK_KIT = BrandKit.from_profile(get_brand("youtube_dark"))


def get_brand_kit(platform_id: str = "youtube_dark") -> BrandKit:
    if platform_id == "youtube_dark":
        return YOUTUBE_DARK_KIT
    return BrandKit.from_profile(get_brand(platform_id))


def score_image_contrast(image_path: Path) -> float:
    """Pontua imagem por contraste e variância — útil para seleção de thumbnail."""

    try:
        from PIL import Image, ImageStat
    except ImportError:
        return 0.0

    try:
        img = Image.open(image_path).convert("L")
        img = img.resize((320, 180))
        stat = ImageStat.Stat(img)
        stddev = stat.stddev[0]
        extrema = stat.extrema[0]
        dynamic_range = extrema[1] - extrema[0]
        return stddev * 0.6 + dynamic_range * 0.4
    except OSError:
        return 0.0
