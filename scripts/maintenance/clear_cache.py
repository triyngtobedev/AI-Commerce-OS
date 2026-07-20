#!/usr/bin/env python3
"""
Limpa caches locais do AI-Commerce-OS (IA, render temp, __pycache__ leve).

Uso:
    python scripts/maintenance/clear_cache.py
    python scripts/maintenance/clear_cache.py --dry-run
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _remove_path(path: Path, *, dry_run: bool) -> bool:
    if not path.exists():
        return False
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        rel = path
    if dry_run:
        print(f"  [dry-run] removeria: {rel}")
        return True
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)
    print(f"  removido: {rel}")
    return True


def clear_cache(*, dry_run: bool = False) -> int:
    removed = 0

    targets: list[Path] = [
        ROOT / "cache",
    ]

    for output_root in (ROOT / "output", ROOT / "downloads"):
        if output_root.is_dir():
            for pattern in (".render_cache", "tmp", "temp"):
                targets.append(output_root / pattern)
            for folder in output_root.rglob("*"):
                if folder.is_dir() and folder.name in {".render_cache", "tmp", "temp"}:
                    targets.append(folder)

    print("\n🧹 Limpando cache do AI-Commerce-OS\n")

    seen: set[Path] = set()
    for target in targets:
        resolved = target.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if _remove_path(resolved, dry_run=dry_run):
            removed += 1

    pycache_count = 0
    for pycache in ROOT.rglob("__pycache__"):
        if not pycache.is_dir():
            continue
        if "venv" in pycache.parts or ".git" in pycache.parts:
            continue
        if _remove_path(pycache, dry_run=dry_run):
            pycache_count += 1

    print(f"\n✅ Concluído — {removed} alvo(s) de cache + {pycache_count} __pycache__\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Limpa caches locais do projeto")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que seria removido sem apagar",
    )
    args = parser.parse_args()
    return clear_cache(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
