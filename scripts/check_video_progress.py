#!/usr/bin/env python3
"""
Mostra progresso de scripts/test_one_video.py em Railway (WebSocket pode cair).

Uso:
  python3 scripts/check_video_progress.py
"""

from __future__ import annotations

import os
from pathlib import Path

LOG_PATH = Path("/app/persistent/logs/test_video.log")
TAIL_LINES = 50


def _get_output_roots() -> list[Path]:
    """Diretórios de saída a inspecionar (Railway e local)."""
    project_root = Path(__file__).resolve().parents[1]
    roots: list[Path] = []

    configured = os.getenv("OUTPUT_DIR", "").strip()
    if configured:
        roots.append(Path(configured))

    for candidate in (project_root / "output", Path("/app/output"), Path("/app/persistent/output")):
        if candidate not in roots:
            roots.append(candidate)

    return roots


def _find_video_final() -> list[Path]:
    videos: list[Path] = []
    seen: set[Path] = set()

    for output_root in _get_output_roots():
        if not output_root.is_dir():
            continue
        for path in output_root.rglob("video_final.mp4"):
            resolved = path.resolve()
            if resolved.is_file() and resolved not in seen:
                seen.add(resolved)
                videos.append(resolved)

    return sorted(videos, key=lambda path: path.stat().st_mtime, reverse=True)


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
    print("\n--- Generated video_final.mp4 files ---")
    if videos:
        for index, path in enumerate(videos, start=1):
            size_bytes = path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            print(f"{index}. {path}")
            print(f"   size: {size_mb:.1f} MB ({size_bytes:,} bytes)")
        print(f"\nTotal: {len(videos)} arquivo(s)")
        return 0

    searched = ", ".join(str(root) for root in _get_output_roots())
    print(f"✗ Nenhum video_final.mp4 encontrado (procurado em: {searched})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
