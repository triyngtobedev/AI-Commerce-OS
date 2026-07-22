#!/usr/bin/env python3
"""Gera icones, page TML e pacotes .tpi / .tpz / .tpp para Touch Portal."""

from __future__ import annotations

import io
import json
import random
import string
import time
import zipfile
from pathlib import Path

import cairosvg
import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugin" / "AI-Commerce-OS"
ICONS_DIR = ROOT / "source" / "icons"
DIST_DIR = ROOT / "dist"
PAGES_DIR = ROOT / "pages"

# slug -> nome fixo do PNG (evita quebra ao rebuildar)
ICON_FILES = {
    "cursor": "aico-cursor.png",
    "visualstudiocode": "aico-vscode.png",
    "folder": "aico-project.png",
    "openai": "aico-pipeline.png",
    "docker": "aico-docker.png",
    "github": "aico-github.png",
    "windowsterminal": "aico-terminal.png",
    "railway": "aico-railway.png",
}

# simple-icons slugs -> acao do plugin
BUTTONS = [
    ("cursor", "open-cursor", "Cursor"),
    ("visualstudiocode", "open-vscode", "VS Code"),
    ("folder", "open-project", "Projeto"),
    ("openai", "pipeline-ia", "Pipeline IA"),
    ("docker", "open-docker", "Docker"),
    ("github", "git-push", "Git Push"),
    ("windowsterminal", "open-terminal", "Terminal"),
    ("railway", "open-railway", "Railway"),
]

FALLBACK_COLORS = {
    "cursor": "#000000",
    "visualstudiocode": "#007ACC",
    "folder": "#FFC107",
    "openai": "#412991",
    "docker": "#2496ED",
    "github": "#181717",
    "windowsterminal": "#4D4D4D",
    "railway": "#0B0D0E",
}


def rand_id() -> str:
    return "u" + "".join(random.choices(string.ascii_lowercase + string.digits, k=11))


SIMPLE_ICONS_TAG = "11.0.0"
SIMPLE_ICONS_SLUG_OVERRIDES = {
    "cursor": ("develop", "cursor"),
}


def fetch_svg(slug: str) -> str:
    if slug in SIMPLE_ICONS_SLUG_OVERRIDES:
        tag, name = SIMPLE_ICONS_SLUG_OVERRIDES[slug]
        url = f"https://raw.githubusercontent.com/simple-icons/simple-icons/{tag}/icons/{name}.svg"
    else:
        url = f"https://raw.githubusercontent.com/simple-icons/simple-icons/{SIMPLE_ICONS_TAG}/icons/{slug}.svg"
    resp = requests.get(url, timeout=15, headers={"User-Agent": "AI-Commerce-OS/1.0"})
    resp.raise_for_status()
    return resp.text


def draw_folder_icon(size: int = 128) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Pasta estilo Explorer (amarela)
    body = (24, size - 28, size - 24, size - 24)
    tab = (24, 36, 72, 52)
    draw.rounded_rectangle(body, radius=6, fill="#FFC107")
    draw.rounded_rectangle(tab, radius=4, fill="#FFD54F")
    draw.rounded_rectangle((24, 48, size - 24, size - 28), radius=6, fill="#FFCA28")
    return img


def draw_icon_from_svg(svg: str, size: int, color: str | None = None) -> Image.Image:
    if color:
        import re

        svg = re.sub(r'fill="[^"]*"', "", svg)
        svg = svg.replace("<path ", f'<path fill="{color}" ')
    png_bytes = cairosvg.svg2png(bytestring=svg.encode(), output_width=size, output_height=size)
    return Image.open(io.BytesIO(png_bytes)).convert("RGBA")


def download_icon(slug: str, size: int = 128) -> Image.Image:
    if slug == "folder":
        return draw_folder_icon(size)
    try:
        svg = fetch_svg(slug)
        color = FALLBACK_COLORS.get(slug)
        return draw_icon_from_svg(svg, size, color)
    except Exception:
        color = FALLBACK_COLORS.get(slug, "#6366f1")
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        r = size // 2 - 8
        cx, cy = size // 2, size // 2
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
        label = slug[:2].upper()
        draw.text((cx - 8, cy - 10), label, fill="white")
        return img


def plugin_action(action_id: str, name: str) -> dict:
    full_id = f"AI-Commerce-OS.actions.{action_id}"
    return {
        "kPlugType": 2,
        "kID": full_id,
        "kPrefix": "AI-Commerce",
        "kInline": "false",
        "kcD": -16777216,
        "kPID": "AI-Commerce-OS",
        "kData": [],
        "kVals": [],
        "kStatic": "true",
        "kcL": -14430369,
        "kDesc": name,
        "kET": 0,
        "KEY_TYPE": "PLUGIN_ACTION",
        "kFormat": name,
        "kName": name,
    }


def make_button(icon_file: str, action_id: str, title: str) -> dict:
    return {
        "A": [plugin_action(action_id, title)],
        "BD": 1,
        "BE": -13421773,
        "BG": -14145496,
        "E": [],
        "I": icon_file,
        "ITS": True,
        "BiR": True,
        "BiT": True,
        "COLS": 1,
        "TA": 5,
        "TC": -1,
        "inS": "",
        "IiS": True,
        "T": "",
        "id": rand_id(),
        "TP": 2,
        "inB": False,
        "TS": -1,
        "inC": 0,
        "ROWS": 1,
    }


def build_page(icon_map: dict[str, str]) -> dict:
    row1, row2 = [], []
    for i, (slug, action_id, title) in enumerate(BUTTONS):
        btn = make_button(icon_map[slug], action_id, title)
        (row1 if i < 4 else row2).append(btn)

    return {
        "BG": -14145496,
        "MAX": False,
        "BGI": "",
        "kGB": False,
        "KEY_ID": str(int(time.time() * 1000)),
        "BUTTONS": [row1, row2],
        "KEY_COLUMNS": 4,
        "kFM": 16,
        "VERSION": 2,
        "KEY_TITLE": "aicommerce-main",
        "KEY_ROWS": 2,
        "BTN_MARGIN": 8,
        "PO": 1,
    }


def write_plugin_icon() -> None:
    img = download_icon("cursor", 24)
    img.save(PLUGIN_DIR / "icon.png")


def zip_dir(src: Path, out: Path, arc_prefix: str | None = None) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in src.rglob("*"):
            if path.is_file():
                if arc_prefix:
                    arc = f"{arc_prefix}/{path.relative_to(src).as_posix()}"
                else:
                    arc = path.name if src.is_dir() else path.relative_to(src.parent).as_posix()
                zf.write(path, arc)


def main() -> None:
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)

    icon_map: dict[str, str] = {}
    for slug, _, _ in BUTTONS:
        filename = ICON_FILES[slug]
        img = download_icon(slug)
        out = ICONS_DIR / filename
        img.save(out, "PNG")
        icon_map[slug] = filename

    write_plugin_icon()

    page = build_page(icon_map)
    tml_path = PAGES_DIR / "aicommerce-main.tml"
    tml_path.write_text(json.dumps(page, separators=(",", ":")), encoding="utf-8")

    # .tpi = zip de PNGs (icon pack)
    tpi_path = DIST_DIR / "AI-Commerce-OS-Icons.tpi"
    with zipfile.ZipFile(tpi_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for png in ICONS_DIR.glob("*.png"):
            zf.write(png, png.name)

    # .tpz = zip com TML + PNGs (page export)
    tpz_path = DIST_DIR / "AI-Commerce-OS-Main.tpz"
    with zipfile.ZipFile(tpz_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(tml_path, "aicommerce-main.tml")
        for png in ICONS_DIR.glob("*.png"):
            zf.write(png, png.name)

    # .tpp = plugin zip
    tpp_path = DIST_DIR / "AI-Commerce-OS.tpp"
    with zipfile.ZipFile(tpp_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in PLUGIN_DIR.rglob("*"):
            if path.is_file():
                zf.write(path, f"AI-Commerce-OS/{path.relative_to(PLUGIN_DIR).as_posix()}")

    print(f"Icones: {len(icon_map)}")
    print(f"TPI: {tpi_path}")
    print(f"TPZ: {tpz_path}")
    print(f"TPP: {tpp_path}")
    print(f"TML: {tml_path}")


if __name__ == "__main__":
    main()
