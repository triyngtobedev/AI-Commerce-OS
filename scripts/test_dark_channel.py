#!/usr/bin/env python3
"""
Teste isolado do Dark Channel Renderer.

Uso:
  python3 scripts/test_dark_channel.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)
load_dotenv(ROOT / ".env.minimal", override=False)

from scripts.video.dark_channel_renderer import render_dark_channel_video

TOPIC = "Os Mistérios das Pirâmides de Gizé"
OUTPUT_DIR = Path("/app/persistent/output/dark_test")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Tema: {TOPIC}")
    print(f"Saída: {OUTPUT_DIR / 'video_final.mp4'}")

    video = render_dark_channel_video(
        TOPIC,
        OUTPUT_DIR,
        output_filename="video_final.mp4",
    )
    print(f"Concluído: {video}")
    return 0 if video.is_file() else 1


if __name__ == "__main__":
    raise SystemExit(main())
