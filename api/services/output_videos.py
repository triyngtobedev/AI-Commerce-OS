"""
Localização de arquivos video_final.mp4 gerados pelo pipeline.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_output_root() -> Path:
    """Diretório base de saída (Railway: OUTPUT_DIR ou /app/persistent/output)."""
    configured = os.getenv("OUTPUT_DIR", "").strip()
    if configured:
        return Path(configured)
    return PROJECT_ROOT / "output"


def find_video_final_files(output_root: Path | None = None) -> list[Path]:
    """Lista video_final.mp4 sob output/, do mais recente ao mais antigo."""
    root = output_root or get_output_root()
    if not root.is_dir():
        return []
    videos = [path for path in root.rglob("video_final.mp4") if path.is_file()]
    return sorted(videos, key=lambda path: path.stat().st_mtime, reverse=True)


def get_latest_video_final(output_root: Path | None = None) -> Path | None:
    """Retorna o video_final.mp4 mais recente, ou None."""
    videos = find_video_final_files(output_root)
    return videos[0] if videos else None
