import os
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



def search_pexels(query):

    """
    Busca mídia no Pexels.

    Ordem:
    
    1 - Vídeos
    2 - Imagens como fallback

    Mantém compatibilidade
    com media_search.py
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



    headers = {
        "Authorization": api_key
    }



    # ==========================
    # 1 - BUSCA VÍDEOS
    # ==========================


    try:

        @retry_with_backoff(max_attempts=3, operation=f"Pexels video search: {query[:40]}")
        def _fetch_videos():
            response = requests.get(
                PEXELS_VIDEO_URL,
                headers=headers,
                params={"query": query, "per_page": 15},
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
                params={"query": query, "per_page": 15},
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