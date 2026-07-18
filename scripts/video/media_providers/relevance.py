"""
Utilitários de relevância para seleção de mídia stock.
"""

from __future__ import annotations

import re

from scripts.video.media_quality import (
    MIN_VIDEO_HEIGHT,
    MIN_VIDEO_HEIGHT_FALLBACK,
    MIN_VIDEO_WIDTH,
    MIN_VIDEO_WIDTH_FALLBACK,
    is_landscape,
    resolution_score,
)

MIN_RELEVANCE_SCORE = 0.48
MIN_PHOTO_RELEVANCE_SCORE = 0.35
MIN_ACCEPTABLE_QUALITY_SCORE = 0.55

# Tags/URLs que indicam gameplay, stock genérico ou aparência amadora.
_REJECT_PATTERNS = re.compile(
    r"\b("
    r"gameplay|gaming|gamer|esports|minecraft|fortnite|roblox|"
    r"twitch|streamer|video[\s_-]?game|playstation|xbox|"
    r"green[\s_-]?screen|chroma|mockup|placeholder|"
    r"office[\s_-]?worker|business[\s_-]?meeting|handshake|"
    r"stock[\s_-]?footage[\s_-]?loop|loopable|"
    r"people[\s_-]?walking|crowd[\s_-]?walking|"
    r"abstract[\s_-]?background|bokeh[\s_-]?background|"
    r"cartoon|animation|animated|3d[\s_-]?render|cgi|"
    r"screenshot|screen[\s_-]?record"
    r")\b",
    re.IGNORECASE,
)

_CINEMATIC_BOOST_PATTERNS = re.compile(
    r"\b("
    r"cinematic|documentary|aerial|drone|timelapse|"
    r"nature|landscape|historical|archive|film|footage|"
    r"4k|uhd|slow[\s_-]?motion|establishing[\s_-]?shot|"
    r"epic|atmospheric|wide[\s_-]?angle"
    r")\b",
    re.IGNORECASE,
)


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-záéíóúâêôãõç0-9]{3,}", text.lower())
    stopwords = {
        "the", "and", "for", "with", "from", "that", "this",
        "uma", "uns", "para", "com", "que", "dos", "das", "por",
        "em", "de", "do", "da", "na", "no", "ao", "os", "as",
        "shot", "scene", "footage", "video", "cinematic", "documentary",
    }
    return {w for w in words if w not in stopwords}


def _video_haystack(video: dict) -> str:
    tags = " ".join(video.get("tags", []))
    url = video.get("url", "")
    user = video.get("user", {}).get("name", "")
    return f"{tags} {url} {user}".lower()


def _looks_generic_or_low_quality(video: dict) -> bool:
    return bool(_REJECT_PATTERNS.search(_video_haystack(video)))


def score_video(query: str, video: dict) -> float:
    """
    Pontua vídeo Pexels/Pixabay por relevância à query da cena.
    Maior = melhor.
    """

    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0.0

    haystack = _video_haystack(video)

    if _looks_generic_or_low_quality(video):
        return 0.0

    matches = sum(1 for token in query_tokens if token in haystack)
    if matches == 0:
        return 0.0

    score = matches / len(query_tokens)

    if matches < max(2, len(query_tokens) // 3):
        score *= 0.55

    width = video.get("width", 0)
    height = video.get("height", 0)

    score += resolution_score(width, height) * 0.75

    if width >= 3840 and height >= 2160:
        score += 0.45
    elif width >= 1920 and height >= 1080:
        score += 0.35
    elif width >= MIN_VIDEO_WIDTH_FALLBACK and height >= MIN_VIDEO_HEIGHT_FALLBACK:
        score += 0.08
    else:
        score -= 0.8

    if not is_landscape(width, height):
        score -= 1.0

    duration = video.get("duration", 0)
    if duration >= 20:
        score += 0.3
    elif duration >= 12:
        score += 0.2
    elif duration >= 8:
        score += 0.1
    elif duration < 5:
        score -= 0.45

    if _CINEMATIC_BOOST_PATTERNS.search(haystack):
        score += 0.18

    return max(0.0, score)


def score_photo(query: str, photo: dict) -> float:
    """Pontua foto por relevância."""

    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0.0

    alt = photo.get("alt", "")
    url = photo.get("url", "")
    photographer = photo.get("photographer", "")
    haystack = f"{alt} {url} {photographer}".lower()

    if _REJECT_PATTERNS.search(haystack):
        return 0.0

    matches = sum(1 for token in query_tokens if token in haystack)
    if matches == 0:
        return 0.0

    score = matches / len(query_tokens)
    if matches < max(2, len(query_tokens) // 3):
        score *= 0.6

    width = photo.get("width", 0)
    height = photo.get("height", 0)
    score += resolution_score(width, height) * 0.5

    if width >= 3840:
        score += 0.3
    elif width >= 1920:
        score += 0.25
    elif width < MIN_VIDEO_WIDTH_FALLBACK:
        score -= 0.5

    return max(0.0, score)


def rank_videos(query: str, videos: list, used_ids: set) -> list[tuple[dict, float]]:
    """Retorna vídeos ranqueados por relevância, excluindo IDs usados."""

    ranked = []

    for video in videos:
        vid = video.get("id")
        if vid and vid in used_ids:
            continue

        item_score = score_video(query, video)
        if item_score <= 0:
            continue

        width = video.get("width", 0)
        height = video.get("height", 0)

        if not is_landscape(width, height):
            continue
        if width < MIN_VIDEO_WIDTH_FALLBACK or height < MIN_VIDEO_HEIGHT_FALLBACK:
            continue

        ranked.append((video, item_score))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def rank_photos(query: str, photos: list, used_ids: set) -> list[tuple[dict, float]]:
    """Retorna fotos ranqueadas por relevância."""

    ranked = []

    for photo in photos:
        pid = photo.get("id")
        if pid and pid in used_ids:
            continue

        item_score = score_photo(query, photo)
        if item_score <= 0:
            continue

        width = photo.get("width", 0)
        height = photo.get("height", 0)

        if width < MIN_VIDEO_WIDTH_FALLBACK or height < MIN_VIDEO_HEIGHT_FALLBACK:
            continue
        if not is_landscape(width, height):
            continue

        ranked.append((photo, item_score))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def pick_best_video(query: str, videos: list, used_ids: set) -> dict | None:
    """Seleciona melhor vídeo não utilizado acima do limiar mínimo."""

    ranked = rank_videos(query, videos, used_ids)

    for video, item_score in ranked:
        if item_score >= MIN_RELEVANCE_SCORE:
            return video

    return None


def pick_ranked_videos(query: str, videos: list, used_ids: set, limit: int = 8) -> list[dict]:
    """Retorna vídeos candidatos acima do limiar mínimo de relevância."""

    ranked = rank_videos(query, videos, used_ids)
    accepted = [
        video for video, item_score in ranked
        if item_score >= MIN_RELEVANCE_SCORE
    ]
    return accepted[:limit]


def pick_best_photo(query: str, photos: list, used_ids: set) -> dict | None:
    """Seleciona melhor foto não utilizada."""

    ranked = rank_photos(query, photos, used_ids)

    for photo, item_score in ranked:
        if item_score >= MIN_PHOTO_RELEVANCE_SCORE:
            return photo

    return None


def pick_ranked_photos(query: str, photos: list, used_ids: set, limit: int = 5) -> list[dict]:
    """Retorna fotos candidatas acima do limiar mínimo de relevância."""

    ranked = rank_photos(query, photos, used_ids)
    accepted = [
        photo for photo, item_score in ranked
        if item_score >= MIN_PHOTO_RELEVANCE_SCORE
    ]
    return accepted[:limit]


def best_video_score(query: str, videos: list, used_ids: set) -> float:
    """Retorna maior score de vídeo disponível (0 se nenhum candidato)."""

    ranked = rank_videos(query, videos, used_ids)
    return ranked[0][1] if ranked else 0.0
