"""
Pixabay Provider — banco de vídeos/imagens gratuito (free tier).

Requer PIXABAY_API_KEY no .env (gratuito em pixabay.com/api/docs).
"""

from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

from scripts.core.production.retry import retry_with_backoff

load_dotenv()

PIXABAY_VIDEO_URL = "https://pixabay.com/api/videos/"
PIXABAY_PHOTO_URL = "https://pixabay.com/api/"

_WARNED_NO_KEY = False


def _warn_missing_key() -> None:
    global _WARNED_NO_KEY

    if _WARNED_NO_KEY:
        return

    _WARNED_NO_KEY = True
    print("AVISO: PIXABAY_API_KEY nao configurada - provedor Pixabay ignorado.")


def search_pixabay(query: str, per_page: int = 15) -> dict:
    """
    Busca vídeos e imagens na Pixabay API.
    Retorna no mesmo formato de search_pexels.
    """

    empty = {"videos": [], "photos": []}

    api_key = os.getenv("PIXABAY_API_KEY")

    if not api_key:
        _warn_missing_key()
        return empty

    params = {
        "key": api_key,
        "q": query,
        "per_page": per_page,
        "safesearch": "true",
    }

    try:
        @retry_with_backoff(max_attempts=3, operation=f"Pixabay video search: {query[:40]}")
        def _fetch_videos():
            response = requests.get(PIXABAY_VIDEO_URL, params=params, timeout=15)
            response.raise_for_status()
            return response.json()

        video_data = _fetch_videos()
    except Exception:
        video_data = {}

    hits = video_data.get("hits", [])

    if hits:
        videos = []
        for hit in hits:
            video_files = []
            videos_dict = hit.get("videos", {})

            for quality in ("large", "medium", "small", "tiny"):
                file_info = videos_dict.get(quality, {})
                if file_info.get("url"):
                    video_files.append({
                        "quality": quality,
                        "link": file_info["url"],
                        "width": file_info.get("width", 0),
                        "height": file_info.get("height", 0),
                    })

            videos.append({
                "id": hit.get("id"),
                "width": hit.get("videos", {}).get("large", {}).get("width", 1920),
                "height": hit.get("videos", {}).get("large", {}).get("height", 1080),
                "duration": hit.get("duration", 0),
                "tags": hit.get("tags", "").split(", "),
                "url": hit.get("pageURL", ""),
                "video_files": video_files,
            })

        return {"tipo": "videos", "videos": videos, "photos": []}

    try:
        @retry_with_backoff(max_attempts=3, operation=f"Pixabay photo search: {query[:40]}")
        def _fetch_photos():
            response = requests.get(
                PIXABAY_PHOTO_URL,
                params={**params, "image_type": "photo"},
                timeout=15,
            )
            response.raise_for_status()
            return response.json()

        photo_data = _fetch_photos()
    except Exception:
        photo_data = {}

    photos = []
    for hit in photo_data.get("hits", []):
        photos.append({
            "id": hit.get("id"),
            "width": hit.get("imageWidth", 0),
            "height": hit.get("imageHeight", 0),
            "alt": hit.get("tags", ""),
            "url": hit.get("pageURL", ""),
            "photographer": hit.get("user", ""),
            "src": {
                "original": hit.get("largeImageURL") or hit.get("webformatURL", ""),
                "large2x": hit.get("imageURL") or hit.get("largeImageURL", ""),
                "large": hit.get("largeImageURL") or hit.get("webformatURL", ""),
                "largeImageURL": hit.get("largeImageURL", ""),
                "webformatURL": hit.get("webformatURL", ""),
            },
        })

    return {"tipo": "images", "videos": [], "photos": photos}
