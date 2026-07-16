import os
import requests
from dotenv import load_dotenv

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

        video_response = requests.get(
            PEXELS_VIDEO_URL,
            headers=headers,
            params={
                "query": query,
                "per_page": 5
            },
            timeout=15
        )


        video_data = (
            video_response.json()
            if video_response.ok
            else {}
        )


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

        photo_response = requests.get(

            PEXELS_PHOTO_URL,

            headers=headers,

            params={
                "query": query,
                "per_page": 5
            },

            timeout=15
        )


        photo_data = (
            photo_response.json()
            if photo_response.ok
            else {}
        )


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