"""
Utilitários de hash para cache e manifesto de produção.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional


def hash_content(data: Any) -> str:
    """Hash SHA-256 de conteúdo JSON-serializável."""

    serialized = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def hash_file(path: Path) -> Optional[str]:
    """Hash SHA-256 de um arquivo. Retorna None se não existir."""

    if not path.exists() or not path.is_file():
        return None

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def hash_files(paths: list[Path]) -> dict[str, Optional[str]]:
    """Hash de múltiplos arquivos."""

    return {str(p): hash_file(p) for p in paths}
