"""
Admin endpoints — limpeza de cache e output.

DELETE /api/v1/admin/cleanup
  Remove /app/persistent/output (mantém a pasta) + /tmp/whisper_cache
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])


def _path_size(path: Path) -> int:
    """Retorna tamanho total em bytes de um diretório ou arquivo."""
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for entry in path.rglob("*"):
        if entry.is_file():
            try:
                total += entry.stat().st_size
            except OSError:
                pass
    return total


def _clean_dir_contents(dir_path: Path) -> int:
    """Remove todo conteúdo de um diretório mantendo a pasta. Retorna bytes liberados."""
    if not dir_path.exists():
        return 0
    freed = 0
    for entry in dir_path.iterdir():
        try:
            if entry.is_file() or entry.is_symlink():
                freed += entry.stat().st_size
                entry.unlink()
            elif entry.is_dir():
                freed += _path_size(entry)
                shutil.rmtree(entry)
        except Exception:
            pass
    return freed


@router.delete("/cleanup")
async def admin_cleanup() -> dict:
    """
    Remove cache e outputs do pipeline para liberar disco.

    Ações:
      1. Deleta todo conteúdo de OUTPUT_DIR (mantém a pasta)
      2. Deleta /tmp/whisper_cache se existir
      3. Retorna espaço liberado em MB

    Requer X-API-Key (autenticado pelo middleware global).
    """
    output_dir_str = os.getenv("OUTPUT_DIR", "/app/persistent/output")
    output_dir = Path(output_dir_str)
    whisper_cache = Path("/tmp/whisper_cache")

    before = shutil.disk_usage(output_dir if output_dir.exists() else Path("/"))
    total_freed = 0

    # 1. Output pipeline
    if output_dir.exists():
        freed = _clean_dir_contents(output_dir)
        total_freed += freed
        print(f"[admin/cleanup] OUTPUT_DIR {output_dir}: {freed / 1e6:.1f} MB liberados")

    # 2. Cache Whisper
    if whisper_cache.exists():
        freed = _path_size(whisper_cache)
        shutil.rmtree(whisper_cache, ignore_errors=True)
        total_freed += freed
        whisper_cache.mkdir(parents=True, exist_ok=True)
        print(f"[admin/cleanup] Whisper cache: {freed / 1e6:.1f} MB liberados")

    after = shutil.disk_usage(output_dir if output_dir.exists() else Path("/"))

    return {
        "status": "ok",
        "espaco_liberado_mb": round(total_freed / 1e6, 2),
        "disco_antes_mb": round(before.free / 1e6, 1),
        "disco_agora_mb": round(after.free / 1e6, 1),
        "output_limpo": str(output_dir),
        "whisper_cache_limpo": not whisper_cache.exists(),
    }
