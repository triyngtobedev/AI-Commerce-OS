"""
Relevance Feedback — registro de auditoria de assets rejeitados.

Este módulo NÃO participa da decisão de mídia: apenas grava, para auditoria
futura, quais candidatos foram descartados e por quê. Nenhuma falha de escrita
pode interromper o pipeline (erros são silenciados).

Motivos de rejeição padronizados:
    generic_content     — relevância baixa / resultado genérico
    repetitive_scene    — muito parecido com cena(s) anterior(es)
    repetitive_framing  — mesmo enquadramento das cenas anteriores
    weak_storytelling   — não atende ao momento narrativo
    wrong_emotion       — incompatível com a emoção da cena
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

REJECTED_ASSETS_FILE = "rejected_assets.json"

VALID_REASONS = {
    "generic_content",
    "repetitive_scene",
    "repetitive_framing",
    "weak_storytelling",
    "wrong_emotion",
}


class RejectionLog:
    """Acumulador simples de rejeições por execução."""

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []

    def record(
        self,
        *,
        scene: int,
        item: dict | None = None,
        score: float = 0.0,
        rejected_reason: str = "generic_content",
        provider: str = "",
        query: str = "",
    ) -> None:
        item = item or {}
        asset_id = item.get("id")
        url = item.get("url") or (item.get("src", {}) or {}).get("original", "")
        self._entries.append({
            "scene": scene,
            "id": asset_id,
            "url": url,
            "score": round(float(score), 4),
            "rejected_reason": rejected_reason,
            "provider": provider,
            "query": query,
        })

    def extend(self, entries: Iterable[dict[str, Any]]) -> None:
        for entry in entries:
            self._entries.append(entry)

    @property
    def entries(self) -> list[dict[str, Any]]:
        return self._entries

    def flush(self, assets_dir: Path) -> None:
        """Grava o log de rejeições. Silencia qualquer erro de I/O."""

        if not self._entries:
            return
        try:
            assets_dir.mkdir(parents=True, exist_ok=True)
            path = assets_dir / REJECTED_ASSETS_FILE
            payload = {
                "total": len(self._entries),
                "rejected": self._entries,
            }
            with open(path, "w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False, indent=4)
        except Exception:
            # Auditoria é best-effort: nunca quebra o pipeline.
            pass
