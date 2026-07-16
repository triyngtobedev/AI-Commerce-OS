"""
Pixabay Provider — banco de vídeos/imagens gratuito (free tier).

Requer PIXABAY_API_KEY no .env (gratuito em pixabay.com/api/docs).
"""

from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

load_dotenv()

PIXABAY_VIDEO_URL = "https://pixabay.com/api/videos/"
PIXABAY_PHOTO_URL = "https://pixabay.com/api/"


def _headers():
    return {}


def search_pixabay(query: str, per_page: int = 15) -> dict:
    """
    Busca mídia no Pixabay.
    Retorna formato compatível com media_search.py.
    """

    api_key = os.getenv("PIXABAY_API_KEY")

    if not api_key:
        return {
            "erro": "PIXABAY_API_KEY não encontrada",
            "videos": [],
            "photos": [],
        }

    params = {
        "key": api_key,
        "q": query,
        "per_page": per_page,
        "safesearch": "true",
    }

    try:
        video_response = requests.get(
            PIXABAY_VIDEO_URL,
            params=params,
            timeout=15,
        )
        video_data = video_response.json() if video_response.ok else {}
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
        photo_response = requests.get(
            PIXABAY_PHOTO_URL,
            params={**params, "image_type": "photo"},
            timeout=15,
        )
        photo_data = photo_response.json() if photo_response.ok else {}
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
