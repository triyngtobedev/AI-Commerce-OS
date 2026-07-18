"""
Sincronização de métricas do YouTube Analytics.

Busca views, watch time, CTR e retenção para cada vídeo registrado
e persiste em database/analytics.json.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from scripts.analytics.video_registry import get_all_videos
from scripts.youtube.youtube_analytics import YouTubeAnalyticsClient

ANALYTICS_FILE = Path("database/analytics.json")


def _load_analytics() -> Dict[str, Any]:
    if not ANALYTICS_FILE.exists():
        return {"last_sync": None, "videos": {}}

    with open(ANALYTICS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        data.setdefault("videos", {})
        return data

    return {"last_sync": None, "videos": {}}


def _save_analytics(data: Dict[str, Any]) -> None:
    ANALYTICS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(ANALYTICS_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def sync_video_metrics(
    client: YouTubeAnalyticsClient,
    video_id: str,
    *,
    days: int = 28,
) -> Optional[Dict[str, Any]]:
    """Busca métricas de um vídeo e retorna dict serializável."""
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        analytics = client.get_video_analytics(
            video_id,
            start_date=start_date,
            end_date=end_date,
        )
        return analytics.to_dict()
    except Exception as exc:
        print(f"⚠️ Erro ao buscar métricas de {video_id}: {exc}")
        return None


def sync_all_videos(*, days: int = 28) -> Dict[str, Any]:
    """
    Sincroniza métricas de todos os vídeos registrados.

    Returns:
        Resumo da sincronização com contagem de sucessos/falhas
    """
    client = YouTubeAnalyticsClient()

    if not client.is_configured():
        return {
            "success": False,
            "message": "Credenciais YouTube Analytics não configuradas",
            "synced": 0,
            "failed": 0,
        }

    videos = get_all_videos()
    store = _load_analytics()
    synced = 0
    failed = 0

    for video in videos:
        video_id = video.get("video_id")
        if not video_id:
            continue

        metrics = sync_video_metrics(client, video_id, days=days)
        if metrics is None:
            failed += 1
            continue

        store["videos"][video_id] = {
            **metrics,
            "topic": video.get("topic", ""),
            "template": video.get("template", ""),
            "title": video.get("title", ""),
            "video_url": video.get("video_url", ""),
            "published_at": video.get("published_at", ""),
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
        synced += 1
        print(f"📊 {video_id}: {metrics.get('views', 0)} views, CTR {metrics.get('ctr', 0):.2%}")

    store["last_sync"] = datetime.now(timezone.utc).isoformat()
    _save_analytics(store)

    summary = {
        "success": True,
        "synced": synced,
        "failed": failed,
        "total_videos": len(videos),
        "last_sync": store["last_sync"],
    }
    print(f"✅ Sincronização concluída: {synced} ok, {failed} falhas")
    return summary


def get_analytics_store() -> Dict[str, Any]:
    return _load_analytics()


def get_video_metrics(video_id: str) -> Optional[Dict[str, Any]]:
    store = _load_analytics()
    return store.get("videos", {}).get(video_id)


def main() -> int:
    result = sync_all_videos()
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
