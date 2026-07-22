"""
Wikimedia Commons Provider — imagens de domínio público via API list=search.

Busca, baixa e (opcionalmente) anima imagens estáticas com Ken Burns.
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import requests

from scripts.core.production.retry import retry_with_backoff
from scripts.video.media_downloader import download_file
from scripts.video.media_quality import MIN_IMAGE_WIDTH_FALLBACK

logger = logging.getLogger(__name__)

COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"

# Apenas extensões de imagem utilizáveis como frame de vídeo
_IMAGE_EXTENSIONS = re.compile(r"\.(jpg|jpeg|png|gif|webp|tiff?|bmp)$", re.IGNORECASE)
REQUEST_TIMEOUT = 15
USER_AGENT = (
    "AI-Commerce-OS/1.0 "
    "(https://github.com/ai-commerce-os; contact: projeto-atlas@example.com)"
)

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
    "Accept-Language": "en",
})


def _build_search_url(query: str, *, limit: int = 6) -> str:
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srnamespace": 6,
        "format": "json",
        "srlimit": limit,
        "origin": "*",
    }
    return f"{COMMONS_API_URL}?{urlencode(params)}"


def _build_credit(extmetadata: dict) -> str:
    artist = extmetadata.get("Artist", {}).get("value", "").strip()
    license_name = extmetadata.get("LicenseShortName", {}).get("value", "").strip()

    parts = []
    if artist:
        parts.append(artist)
    if license_name:
        parts.append(license_name)

    return " — ".join(parts)


def _is_image_url(url: str) -> bool:
    """True se a URL termina em extensão de imagem utilizável como frame."""
    return bool(_IMAGE_EXTENSIONS.search(url))


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

        # Filtra .djvu, .pdf, .ogg, .ogv, .webm e outros não-imagem
        if not _is_image_url(url):
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
            "page_url": page.get("canonicalurl") or page.get("fullurl", ""),
        })

    return photos


def _fetch_imageinfo_for_titles(titles: list[str]) -> dict:
    if not titles:
        return {}

    @retry_with_backoff(max_attempts=3, operation=f"Wikimedia imageinfo: {titles[0][:40]}")
    def _fetch():
        response = _SESSION.get(
            COMMONS_API_URL,
            params={
                "action": "query",
                "titles": "|".join(titles),
                "prop": "imageinfo",
                "iiprop": "url|size|extmetadata",
                "format": "json",
                "formatversion": 2,
                "origin": "*",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    data = _fetch()
    pages = data.get("query", {}).get("pages", {})
    if isinstance(pages, list):
        pages = {str(page.get("pageid", idx)): page for idx, page in enumerate(pages)}
    return pages


def _search_titles(query: str, *, limit: int = 6) -> list[str]:
    search_url = _build_search_url(query, limit=limit)
    logger.debug("[Wikimedia] Search URL: %s", search_url)
    print(f"[Wikimedia] Search URL: {search_url}")

    @retry_with_backoff(max_attempts=3, operation=f"Wikimedia search: {query[:40]}")
    def _fetch():
        response = _SESSION.get(
            COMMONS_API_URL,
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srnamespace": 6,
                "format": "json",
                "srlimit": limit,
                "origin": "*",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    try:
        data = _fetch()
    except Exception as error:
        logger.warning("[Wikimedia] Search failed for %r: %s", query, error)
        print(f"[Wikimedia] Search failed for {query!r}: {error}")
        return []

    hits = data.get("query", {}).get("search", [])
    titles = [hit.get("title", "") for hit in hits if hit.get("title")]
    logger.debug("[Wikimedia] Search returned %d titles for %r: %s", len(titles), query, titles)
    print(
        f"[Wikimedia] Search returned {len(titles)} result(s) for {query!r}: "
        f"{titles[:3]}"
    )
    return titles


def _one_word_fallback(query: str) -> str:
    words = [word for word in query.split() if len(word) > 2]
    if not words:
        return query.strip()
    return words[0]


def search_wikimedia(query: str, limit: int = 6) -> dict:
    """
    Busca imagens no Wikimedia Commons via list=search + imageinfo.

    Se a query completa não retornar resultados, tenta a primeira palavra.
    """

    empty = {"videos": [], "photos": []}

    if not query or not query.strip():
        return empty

    search_query = " ".join(query.split())[:100].strip()
    queries_to_try = [search_query]
    simplified = _one_word_fallback(search_query)
    if simplified and simplified.lower() != search_query.lower():
        queries_to_try.append(simplified)

    for attempt_query in queries_to_try:
        titles = _search_titles(attempt_query, limit=limit * 3)
        if not titles:
            continue

        try:
            pages = _fetch_imageinfo_for_titles(titles[: limit * 2])
        except Exception as error:
            logger.warning("[Wikimedia] imageinfo failed for %r: %s", attempt_query, error)
            print(f"[Wikimedia] imageinfo failed for {attempt_query!r}: {error}")
            continue

        photos = _parse_pages(pages, limit)
        if photos:
            print(
                f"[Wikimedia] Selected {len(photos)} photo(s) for {attempt_query!r} "
                f"(first: {photos[0]['src']['original'][:80]}...)"
            )
            return {
                "tipo": "images",
                "videos": [],
                "photos": photos,
            }

        print(f"[Wikimedia] No usable photos after filtering for {attempt_query!r}")

    return empty


def download_first_image(
    query: str,
    output_path: str | Path,
    *,
    assets_dir: Optional[str | Path] = None,
) -> Optional[Path]:
    """
    Busca no Commons e baixa a primeira imagem válida para output_path.
    """

    result = search_wikimedia(query, limit=3)
    photos = result.get("photos", [])
    if not photos:
        print(f"[Wikimedia] No image to download for query: {query!r}")
        return None

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if assets_dir:
        assets_path = Path(assets_dir)
        assets_path.mkdir(parents=True, exist_ok=True)

    url = photos[0]["src"]["original"]
    print(f"[Wikimedia] Downloading image: {url}")

    try:
        download_file(url, destination)
    except Exception as error:
        print(f"[Wikimedia] Download failed: {error}")
        return None

    if destination.exists() and destination.stat().st_size > 0:
        print(f"[Wikimedia] Saved image to {destination.resolve()}")
        return destination

    return None


def create_ken_burns_video(
    image_path: str | Path,
    output_path: str | Path,
    *,
    duration: float = 10.0,
) -> bool:
    """
    Anima imagem estática com efeito Ken Burns (zoom lento).
    """

    source = Path(image_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    frames = max(1, int(duration * 25))
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(source.resolve()),
        "-vf",
        (
            "scale=1920:1080,"
            "zoompan=z='min(zoom+0.001,1.3)':d=250:"
            "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        ),
        "-t", str(duration),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(output),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        if output.exists():
            print(f"[Wikimedia] Ken Burns video saved: {output.resolve()}")
            return True
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode("utf-8", errors="replace") if error.stderr else ""
        print(f"[Wikimedia] Ken Burns failed: {stderr[:200]}")

    return False


def test_wikimedia_search(query: str = "ancient Egypt pyramid") -> bool:
    """Smoke test — confirma que a API Commons retorna imagens."""

    result = search_wikimedia(query, limit=1)
    ok = bool(result.get("photos"))
    print(f"[Wikimedia] Test search {query!r}: {'OK' if ok else 'FAILED'}")
    return ok
