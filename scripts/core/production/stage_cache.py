"""
Cache inteligente por etapa do pipeline.

Evita reprocessamento quando inputs e outputs permanecem válidos.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from scripts.core.production.hash_utils import hash_content, hash_file


class StageCache:
    """Gerencia cache por etapa com hashes de input/output."""

    CACHE_FILENAME = "stage_cache.json"

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self._path = output_dir / self.CACHE_FILENAME
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            with open(self._path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        return {"stages": {}}

    def save(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as handle:
            json.dump(self._data, handle, ensure_ascii=False, indent=2)

    def is_valid(
        self,
        stage: str,
        input_data: Any,
        output_files: list[Path],
    ) -> bool:
        """Verifica se etapa pode ser pulada (cache hit)."""

        stage_data = self._data.get("stages", {}).get(stage)
        if not stage_data:
            return False

        current_input_hash = hash_content(input_data)
        if stage_data.get("input_hash") != current_input_hash:
            return False

        for path in output_files:
            if not path.exists():
                return False

            stored_hash = stage_data.get("output_hashes", {}).get(str(path))
            current_hash = hash_file(path)
            if stored_hash != current_hash:
                return False

        return True

    def record(
        self,
        stage: str,
        input_data: Any,
        output_files: list[Path],
        *,
        extra: Optional[dict] = None,
    ):
        """Registra cache após execução bem-sucedida."""

        output_hashes = {}
        for path in output_files:
            file_hash = hash_file(path)
            if file_hash:
                output_hashes[str(path)] = file_hash

        entry = {
            "input_hash": hash_content(input_data),
            "output_hashes": output_hashes,
        }
        if extra:
            entry.update(extra)

        self._data.setdefault("stages", {})[stage] = entry
        self.save()

    def invalidate_from(self, stage: str, stage_order: list[str]):
        """Invalida etapa e todas as subsequentes."""

        if stage not in stage_order:
            return

        idx = stage_order.index(stage)
        for s in stage_order[idx:]:
            self._data.get("stages", {}).pop(s, None)
        self.save()
