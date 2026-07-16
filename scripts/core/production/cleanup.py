"""
Limpeza de arquivos temporários após produção.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from scripts.core.production.logger import get_logger

TEMP_PATTERNS = (
    "*.tmp",
    "*.temp",
    "*_temp.*",
    ".render_cache",
)


def cleanup_temp_files(output_dir: Path, *, dry_run: bool = False) -> list[str]:
    """
    Remove arquivos temporários do diretório de produção.

    Preserva artefatos finais (video_final.mp4, manifest, JSONs).
    """

    logger = get_logger("cleanup")
    removed = []

    temp_dirs = [
        output_dir / ".render_cache",
        output_dir / "tmp",
        output_dir / "temp",
    ]

    for temp_dir in temp_dirs:
        if temp_dir.exists() and temp_dir.is_dir():
            if dry_run:
                removed.append(str(temp_dir))
            else:
                shutil.rmtree(temp_dir, ignore_errors=True)
                removed.append(str(temp_dir))

    for pattern in TEMP_PATTERNS:
        if pattern.startswith("."):
            continue
        for path in output_dir.rglob(pattern):
            if path.is_file():
                if dry_run:
                    removed.append(str(path))
                else:
                    try:
                        path.unlink()
                        removed.append(str(path))
                    except OSError:
                        pass

    if removed:
        logger.info(f"Limpeza: {len(removed)} item(ns) temporário(s) removido(s)")
    else:
        logger.info("Limpeza: nenhum arquivo temporário encontrado")

    return removed
