#!/usr/bin/env python3
"""
Mostra progresso de scripts/test_one_video.py em Railway (WebSocket pode cair).

Uso:
  python3 scripts/check_video_progress.py
"""

from __future__ import annotations

import sys
from pathlib import Path

LOG_PATH = Path("/app/persistent/logs/test_video.log")
TAIL_LINES = 50


def _find_video_final() -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    output = root / "output"
    if not output.is_dir():
        return []
    return sorted(output.rglob("video_final.mp4"))


def main() -> int:
    print(f"Log: {LOG_PATH}")
    if LOG_PATH.is_file():
        lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = lines[-TAIL_LINES:] if len(lines) > TAIL_LINES else lines
        print(f"\n--- últimas {len(tail)} linhas ---")
        for line in tail:
            print(line)
    else:
        print("(arquivo de log ainda não existe)")

    videos = _find_video_final()
    print("\n--- video_final.mp4 ---")
    if videos:
        for path in videos:
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"✓ {path} ({size_mb:.1f} MB)")
        return 0

    print("✗ Nenhum video_final.mp4 encontrado em output/")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
