"""
Wikimedia Commons Provider — imagens de domínio público / arquivo histórico.

Usa a API pública do Wikimedia Commons (sem API key).
"""

from __future__ import annotations

import requests

from scripts.core.production.retry import retry_with_backoff
from scripts.video.media_quality import MIN_IMAGE_WIDTH_FALLBACK

COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
REQUEST_TIMEOUT = 10
USER_AGENT = "AI-Commerce-OS/1.0 (documentary pipeline; contact: projeto-atlas)"


def _build_credit(extmetadata: dict) -> str:
    artist = extmetadata.get("Artist", {}).get("value", "").strip()
    license_name = extmetadata.get("LicenseShortName", {}).get("value", "").strip()

    parts = []
    if artist:
        parts.append(artist)
    if license_name:
        parts.append(license_name)

    return " — ".join(parts)


def _parse_pages(pages: dict, limit: int) -> list[dict]:
    photos = []

    for page in pages.values():
        if len(photos) >= limit:
            break

        imageinfo = page.get("imageinfo", [])
        if not imageinfo:
            continue

        info = imageinfo[0]
        width = info.get("width", 0)
        height = info.get("height", 0)

        if width < MIN_IMAGE_WIDTH_FALLBACK:
            continue

        url = info.get("url", "")
        if not url:
            continue

        extmetadata = info.get("extmetadata", {})

        photos.append({
            "id": page.get("pageid"),
            "width": width,
            "height": height,
            "src": {
                "original": url,
                "large2x": url,
                "large": url,
            },
            "credit": _build_credit(extmetadata),
        })

    return photos


def search_wikimedia(query: str, limit: int = 6) -> dict:
    """
    Busca imagens de domínio público / licença livre no Wikimedia Commons.

    Retorna no mesmo formato de search_pexels, populando apenas "photos".
    """

    empty = {"videos": [], "photos": []}

    if not query or not query.strip():
        return empty

    try:
        @retry_with_backoff(max_attempts=3, operation=f"Wikimedia search: {query[:40]}")
        def _fetch():
            response = requests.get(
                COMMONS_API_URL,
                params={
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": query.strip()[:120],
                    "gsrnamespace": 6,
                    "gsrlimit": limit * 3,
                    "prop": "imageinfo",
                    "iiprop": "url|size|extmetadata",
                    "format": "json",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()

        data = _fetch()

    except Exception:
        return empty

    pages = data.get("query", {}).get("pages", {})
    photos = _parse_pages(pages, limit)

    if not photos:
        return empty

    return {
        "tipo": "images",
        "videos": [],
        "photos": photos,
    }
