import os
import re
import requests
from dotenv import load_dotenv

from scripts.core.production.retry import retry_with_backoff

load_dotenv()


PEXELS_VIDEO_URL = (
    "https://api.pexels.com/videos/search"
)

PEXELS_PHOTO_URL = (
    "https://api.pexels.com/v1/search"
)

# Palavras abstratas que Pexels/Pixabay não indexam — remover antes de buscar
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
    """
    Reduz query para 2-3 palavras visuais concretas que Pexels/Pixabay
    conseguem indexar. Remove modificadores abstratos.

    Ex: "roman legions barbarian invasion" -> "roman soldiers"
        "roman senate corruption ancient" -> "roman senate"
        "ancient egypt pyramid mystery" -> "egypt pyramid"
    """
    words = query.strip().split()
    if not words:
        return query

    filtered = [w for w in words if w.lower() not in _ABSTRACT_STOPWORDS]
    if not filtered:
        filtered = words[:max_words]
    return " ".join(filtered[:max_words]).strip()


def search_pexels(
    query,
    *,
    orientation="landscape",
    min_width=1920,
    min_height=1080,
    size=None,
    per_page=15,
):

    """
    Busca mídia no Pexels.

    Ordem:

    1 - Vídeos
    2 - Imagens como fallback

    Filtros de qualidade/orientação:
        orientation — "landscape" (YouTube) ou "portrait" (TikTok/vertical).
        min_width/min_height — piso de resolução (default Full HD, inclui 4K).
        size — tier opcional do Pexels ("large"=4K, "medium"=Full HD, "small"=HD).

    Mantém compatibilidade com media_search.py (query posicional).
    """


    api_key = os.getenv(
        "PEXELS_API_KEY"
    )


    if not api_key:

        return {
            "erro": (
                "PEXELS_API_KEY não encontrada"
            ),
            "videos": [],
            "photos": []
        }



    # Simplifica query para termos visuais — Pexels não indexa conceitos abstratos
    simple_query = _simplify_for_stock(query)
    if simple_query != query:
        print(f"[Pexels] Query simplificada: {query!r} -> {simple_query!r}")

    headers = {
        "Authorization": api_key
    }

    video_params = {
        "query": simple_query,
        "per_page": per_page,
        "orientation": orientation,
        "min_width": min_width,
        "min_height": min_height,
    }

    photo_params = {
        "query": simple_query,
        "per_page": per_page,
        "orientation": orientation,
    }

    if size:
        video_params["size"] = size
        photo_params["size"] = size



    # ==========================
    # 1 - BUSCA VÍDEOS
    # ==========================


    try:

        @retry_with_backoff(max_attempts=3, operation=f"Pexels video search: {query[:40]}")
        def _fetch_videos():
            response = requests.get(
                PEXELS_VIDEO_URL,
                headers=headers,
                params=video_params,
                timeout=15,
            )
            response.raise_for_status()
            return response.json()

        video_data = _fetch_videos()

    except Exception:

        video_data = {}



    videos = video_data.get(
        "videos",
        []
    )



    if videos:

        return {

            "tipo": "videos",

            "videos": videos,

            "photos": []

        }



    # ==========================
    # 2 - FALLBACK IMAGENS
    # ==========================


    try:

        @retry_with_backoff(max_attempts=3, operation=f"Pexels photo search: {query[:40]}")
        def _fetch_photos():
            response = requests.get(
                PEXELS_PHOTO_URL,
                headers=headers,
                params=photo_params,
                timeout=15,
            )
            response.raise_for_status()
            return response.json()

        photo_data = _fetch_photos()

    except Exception:

        photo_data = {}



    return {

        "tipo": "images",

        "videos": [],

        "photos": photo_data.get(
            "photos",
            []
        )

    }