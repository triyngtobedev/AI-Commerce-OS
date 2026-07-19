"""
YouTube Creative Commons Provider — footage via yt-dlp.

Busca vídeos licenciados como Creative Commons no YouTube e baixa
até 1 clipe por cena (720p, 60s). Falha silenciosamente se yt-dlp
não estiver disponível ou nenhum resultado CC for encontrado.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

FOOTAGE_ROOT = Path("assets/footage/cc_youtube")
MAX_DURATION_SECONDS = 60
MAX_HEIGHT = 720
SEARCH_RESULTS = 5


def _yt_dlp_available() -> bool:
    return shutil.which("yt-dlp") is not None


def _run_yt_dlp(args: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess | None:
    if not _yt_dlp_available():
        return None

    try:
        return subprocess.run(
            ["yt-dlp", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return None


def _search_cc_entries(visual_query: str) -> list[dict]:
    """Retorna entradas de vídeo CC via yt-dlp ytsearch."""
    search_term = f"{visual_query} creative commons"
    result = _run_yt_dlp(
        [
            f"ytsearch{SEARCH_RESULTS}:{search_term}",
            "--match-filter",
            "license *= 'Creative Commons'",
            "--dump-json",
            "--no-download",
            "--no-playlist",
        ],
        timeout=90,
    )
    if not result or result.returncode != 0:
        return []

    entries: list[dict] = []
    for line in (result.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("_type") == "url" and entry.get("url"):
            entries.append(entry)
        elif entry.get("id"):
            entries.append(entry)

    return entries


def _download_entry(
    entry: dict,
    output_dir: Path,
    *,
    max_duration: int = MAX_DURATION_SECONDS,
    max_height: int = MAX_HEIGHT,
) -> tuple[Path | None, dict]:
    """Baixa um vídeo CC e retorna path + metadados de atribuição."""
    output_dir.mkdir(parents=True, exist_ok=True)

    video_url = entry.get("webpage_url") or entry.get("url") or ""
    if not video_url and entry.get("id"):
        video_url = f"https://www.youtube.com/watch?v={entry['id']}"

    if not video_url:
        return None, {}

    output_template = str(output_dir / "%(title).80B.%(ext)s")
    format_selector = (
        f"bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/"
        f"best[height<={max_height}][ext=mp4]/"
        f"best[height<={max_height}]"
    )

    result = _run_yt_dlp(
        [
            video_url,
            "--match-filter",
            "license *= 'Creative Commons'",
            "-f",
            format_selector,
            "--merge-output-format",
            "mp4",
            "--max-downloads",
            "1",
            "--download-sections",
            f"*0-{max_duration}",
            "-o",
            output_template,
            "--no-playlist",
            "--no-overwrites",
            "--restrict-filenames",
        ],
        timeout=180,
    )

    if not result or result.returncode != 0:
        return None, {}

    clips = sorted(output_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not clips:
        clips = sorted(output_dir.glob("*.*"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not clips:
        return None, {}

    clip_path = clips[0]
    attribution = {
        "title": entry.get("title") or clip_path.stem,
        "author": entry.get("uploader") or entry.get("channel") or "Unknown",
        "url": video_url,
        "license": entry.get("license") or "Creative Commons",
        "provider": "youtube_cc",
    }
    return clip_path, attribution


def search_and_download_cc_footage(
    visual_query: str,
    scene_id: str,
    *,
    max_duration: int = MAX_DURATION_SECONDS,
    max_height: int = MAX_HEIGHT,
) -> dict | None:
    """
    Busca e baixa 1 clipe CC do YouTube para a cena.

    Returns:
        {"clip_path": Path, "attribution": {...}} ou None se falhar.
    """
    if not visual_query or not visual_query.strip():
        return None

    if not _yt_dlp_available():
        return None

    output_dir = FOOTAGE_ROOT / scene_id
    entries = _search_cc_entries(visual_query.strip())
    if not entries:
        return None

    for entry in entries:
        clip_path, attribution = _download_entry(
            entry,
            output_dir,
            max_duration=max_duration,
            max_height=max_height,
        )
        if clip_path and clip_path.exists() and clip_path.stat().st_size > 0:
            return {
                "clip_path": clip_path,
                "attribution": attribution,
            }

    return None


def try_youtube_cc_footage(
    visual_query: str,
    scene_id: str,
    output_path: Path,
    *,
    ledger=None,
    scene_num: int = 0,
) -> dict | None:
    """
    Tenta obter footage CC e copia para output_path do pipeline.

    Falha silenciosamente — retorna None em qualquer erro.
    """
    try:
        result = search_and_download_cc_footage(visual_query, scene_id)
        if not result:
            return None

        clip_path = Path(result["clip_path"])
        if not clip_path.exists():
            return None

        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(clip_path, output_path)

        attribution = result.get("attribution") or {}
        if ledger:
            ledger.register_asset(
                source="youtube_cc",
                provider="youtube_cc",
                license_text=attribution.get("license", "Creative Commons"),
                media_type="video",
                scene_id=scene_num,
                local_path=output_path,
                creator=attribution.get("author", ""),
                source_url=attribution.get("url", ""),
                credit=f"{attribution.get('title', '')} — {attribution.get('author', '')}",
                visual_quality_score=0.7,
            )

        return {
            "saved": True,
            "media_type": "video",
            "source": f"youtube_cc:{visual_query}",
            "provedor": "youtube_cc",
            "quality_score": 0.7,
            "attribution": attribution,
        }
    except Exception:
        return None
