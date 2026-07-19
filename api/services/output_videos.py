"""
Localização de arquivos video_final.mp4 gerados pelo pipeline.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Ordem de busca: Railway runtime, volume persistente, dev local
OUTPUT_SEARCH_ROOTS = (
    Path("/app/output"),
    Path("/app/persistent/output"),
    PROJECT_ROOT / "output",
)


def get_output_search_roots() -> list[Path]:
    """Diretórios inspecionados em ordem de prioridade."""
    return list(OUTPUT_SEARCH_ROOTS)


def find_video_final_files() -> list[Path]:
    """Lista video_final.mp4 em todos os diretórios de saída, mais recente primeiro."""
    videos: list[Path] = []
    seen: set[Path] = set()

    for root in get_output_search_roots():
        if not root.is_dir():
            continue
        for path in root.glob("**/video_final.mp4"):
            resolved = path.resolve()
            if resolved.is_file() and resolved not in seen:
                seen.add(resolved)
                videos.append(resolved)

    return sorted(videos, key=lambda path: path.stat().st_mtime, reverse=True)


def get_latest_video_final() -> Path | None:
    """Retorna o video_final.mp4 mais recente, ou None."""
    videos = find_video_final_files()
    return videos[0] if videos else None


def is_allowed_output_path(video_path: Path) -> bool:
    """True se o arquivo estiver sob um dos diretórios de saída permitidos."""
    resolved = video_path.resolve()
    for root in get_output_search_roots():
        if not root.is_dir():
            continue
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False
