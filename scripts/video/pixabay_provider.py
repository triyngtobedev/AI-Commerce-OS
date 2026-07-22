"""
Pixabay Provider — banco de vídeos/imagens gratuito (free tier).

Requer PIXABAY_API_KEY no .env (gratuito em pixabay.com/api/docs).
"""

from __future__ import annotations

import os
import re

import requests
from dotenv import load_dotenv

from scripts.core.production.retry import retry_with_backoff

load_dotenv()

# Mesmo conjunto de stopwords abstratas usado no Pexels
_ABSTRACT_STOPWORDS = frozenset({
    "invasion", "corruption", "decline", "consequence", "impact", "mystery",
    "legacy", "revelation", "investigation", "discovery", "truth", "secrets",
    "hidden", "forgotten", "ancient", "historical", "documentary", "cinematic",
    "dramatic", "atmospheric", "moody", "tension", "conflict", "struggle",
    "destruction", "devastation", "aftermath", "crisis", "conspiracy",
    "theory", "evidence", "research", "analysis", "exploration",
    "phenomenon", "enigma", "cover-up", "reveal", "exposed", "classified",
    "unsolved", "enduring", "profound", "unveiled", "untold",
    "barbarian", "barbarians", "legion", "legions",
    "senate", "senatorial", "emperor", "emperors",
    "empire", "kingdom", "republic",
})


def _simplify_for_stock(query: str, max_words: int = 3) -> str:
    words = query.strip().split()
    if not words:
        return query
    filtered = [w for w in words if w.lower() not in _ABSTRACT_STOPWORDS]
    if not filtered:
        filtered = words[:max_words]
    return " ".join(filtered[:max_words]).strip()

PIXABAY_VIDEO_URL = "https://pixabay.com/api/videos/"
PIXABAY_PHOTO_URL = "https://pixabay.com/api/"

_WARNED_NO_KEY = False


def _warn_missing_key() -> None:
    global _WARNED_NO_KEY

    if _WARNED_NO_KEY:
        return

    _WARNED_NO_KEY = True
    print("AVISO: PIXABAY_API_KEY nao configurada - provedor Pixabay ignorado.")


def _shorten_pixabay_query(query: str, max_len: int = 60) -> str:
    cleaned = " ".join(query.split()).strip()
    if len(cleaned) <= max_len:
        return cleaned

    words = cleaned.split()
    result = []
    length = 0
    for word in words[:8]:
        next_len = length + len(word) + (1 if result else 0)
        if next_len > max_len:
            break
        result.append(word)
        length = next_len

    return " ".join(result).strip() or cleaned[:max_len].strip()


def test_pixabay_api(query: str = "documentary historical") -> bool:
    """
    Smoke test — confirma leitura de PIXABAY_API_KEY e resposta da API.
    """

    api_key = os.getenv("PIXABAY_API_KEY")
    if not api_key:
        _warn_missing_key()
        print("[Pixabay] Test FAILED — PIXABAY_API_KEY not set")
        return False

    masked = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "****"
    print(f"[Pixabay] PIXABAY_API_KEY loaded ({masked})")

    try:
        response = requests.get(
            PIXABAY_PHOTO_URL,
            params={
                "key": api_key,
                "q": query,
                "per_page": 3,
                "safesearch": "true",
            },
            timeout=15,
        )
        response.raise_for_status()
        hits = response.json().get("hits", [])
        ok = len(hits) > 0
        print(
            f"[Pixabay] Test search {query!r}: "
            f"{'OK' if ok else 'FAILED'} ({len(hits)} hit(s))"
        )
        return ok
    except Exception as error:
        print(f"[Pixabay] Test FAILED — {error}")
        return False


def search_pixabay(
    query: str,
    per_page: int = 15,
    *,
    orientation: str = "all",
    min_width: int = 1920,
    min_height: int = 1080,
) -> dict:
    """
    Busca vídeos e imagens na Pixabay API.
    Retorna no mesmo formato de search_pexels.

    Filtros de qualidade/orientação:
        min_width/min_height — piso de resolução (default Full HD, inclui 4K).
            Para vertical (TikTok) use min_width=1080, min_height=1920 — a API
            de vídeos da Pixabay não expõe `orientation`, então a orientação é
            forçada via dimensões mínimas.
        orientation — "all" | "horizontal" | "vertical" (aplicado às imagens).
    """

    empty = {"videos": [], "photos": []}

    api_key = os.getenv("PIXABAY_API_KEY")

    if not api_key:
        _warn_missing_key()
        return empty

    print(f"[Pixabay] Searching: {query!r}")

    # Simplifica para termos visuais antes de encurtar
    simplified = _simplify_for_stock(query)
    if simplified != query:
        print(f"[Pixabay] Query simplificada: {query!r} -> {simplified!r}")
    query = _shorten_pixabay_query(simplified)

    params = {
        "key": api_key,
        "q": query,
        "per_page": per_page,
        "safesearch": "true",
        "min_width": min_width,
        "min_height": min_height,
    }

    try:
        @retry_with_backoff(max_attempts=3, operation=f"Pixabay video search: {query[:40]}")
        def _fetch_videos():
            response = requests.get(PIXABAY_VIDEO_URL, params=params, timeout=15)
            if response.status_code == 400 and len(query.split()) > 2:
                shorter = _shorten_pixabay_query(query, max_len=40)
                response = requests.get(
                    PIXABAY_VIDEO_URL,
                    params={**params, "q": shorter},
                    timeout=15,
                )
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
        # A API de imagens da Pixabay aceita `orientation` (all/horizontal/vertical).
        photo_params = {**params, "image_type": "photo", "orientation": orientation}

        @retry_with_backoff(max_attempts=3, operation=f"Pixabay photo search: {query[:40]}")
        def _fetch_photos():
            response = requests.get(
                PIXABAY_PHOTO_URL,
                params=photo_params,
                timeout=15,
            )
            if response.status_code == 400 and len(query.split()) > 2:
                shorter = _shorten_pixabay_query(query, max_len=40)
                response = requests.get(
                    PIXABAY_PHOTO_URL,
                    params={**photo_params, "q": shorter},
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
