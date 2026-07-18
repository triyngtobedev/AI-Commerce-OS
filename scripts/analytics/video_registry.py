"""
Registro persistente de vídeos publicados no YouTube.

Salva metadados após upload bem-sucedido em database/videos.json.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VIDEOS_FILE = Path("database/videos.json")


def _load_videos() -> List[Dict[str, Any]]:
    if not VIDEOS_FILE.exists():
        return []

    with open(VIDEOS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data if isinstance(data, list) else []


def _save_videos(records: List[Dict[str, Any]]) -> None:
    VIDEOS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(VIDEOS_FILE, "w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)


def register_video(
    *,
    video_id: str,
    video_url: str,
    topic: str = "",
    template: str = "",
    title: str = "",
    output_folder: str = "",
    job_id: Optional[str] = None,
    privacy_status: str = "unlisted",
) -> Dict[str, Any]:
    """
    Registra ou atualiza um vídeo publicado no YouTube.
    """
    records = _load_videos()
    now = datetime.now(timezone.utc).isoformat()

    record = {
        "video_id": video_id,
        "video_url": video_url,
        "topic": topic,
        "template": template,
        "title": title,
        "published_at": now,
        "output_folder": output_folder,
        "job_id": job_id,
        "privacy_status": privacy_status,
    }

    for index, existing in enumerate(records):
        if existing.get("video_id") == video_id:
            record["published_at"] = existing.get("published_at", now)
            records[index] = {**existing, **record}
            _save_videos(records)
            return records[index]

    records.append(record)
    _save_videos(records)
    return record


def get_videos_since(days: int = 7) -> List[Dict[str, Any]]:
    """Retorna vídeos publicados nos últimos N dias."""
    cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
    results: List[Dict[str, Any]] = []

    for record in _load_videos():
        published = record.get("published_at", "")
        try:
            ts = datetime.fromisoformat(published.replace("Z", "+00:00")).timestamp()
        except ValueError:
            continue

        if ts >= cutoff:
            results.append(record)

    return results


def get_all_videos() -> List[Dict[str, Any]]:
    return _load_videos()
