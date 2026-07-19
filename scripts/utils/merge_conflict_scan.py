"""Detecta marcadores de conflito de merge Git em arquivos Python."""

from __future__ import annotations

from pathlib import Path

_CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")


def find_merge_conflicts(root: Path | None = None) -> list[dict[str, int | str]]:
    """Retorna lista de {path, line} para cada marcador de conflito encontrado."""

    base = root or Path(__file__).resolve().parents[2]
    hits: list[dict[str, int | str]] = []

    for path in sorted(base.rglob("*.py")):
        if ".git" in path.parts or "node_modules" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            stripped = line.lstrip()
            if any(stripped.startswith(marker) for marker in _CONFLICT_MARKERS):
                hits.append({"path": str(path.relative_to(base)), "line": line_no})

    return hits
