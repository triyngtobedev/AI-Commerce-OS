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

# Mapeamento de temas históricos/específicos → queries visuais que existem
# no Pexels/Pixabay. A chave é uma palavra da query original; o valor é
# a query stock que sabemos que retorna resultados.
_HISTORICAL_STOCK_MAP = {
    "rome": "ancient rome",
    "roman": "ancient rome",
    "egito": "ancient egypt",
    "egypt": "ancient egypt",
    "egipcio": "ancient egypt",
    "egípcio": "ancient egypt",
    "grecia": "ancient greece",
    "greece": "ancient greece",
    "greek": "ancient greece",
    "medieval": "medieval castle",
    "idade media": "medieval castle",
    "temple": "ancient temple",
    "templo": "ancient temple",
    "pyramid": "egypt pyramid",
    "piramide": "egypt pyramid",
    "pirâmide": "egypt pyramid",
    "soldier": "roman soldier",
    "soldiers": "soldiers army",
    "soldado": "soldiers army",
    "war": "war battle soldiers",
    "guerra": "war battle",
    "battle": "battle soldiers",
    "batalha": "battle soldiers",
    "king": "king crown throne",
    "rei": "king crown throne",
    "queen": "queen crown",
    "rainha": "queen crown",
    "emperor": "emperor crown",
    "imperador": "emperor crown",
    "sword": "sword weapon",
    "espada": "sword weapon",
    "ship": "ship ocean sailing",
    "navio": "ship ocean sailing",
    "barco": "boat ship sailing",
    "horse": "horse riding",
    "cavalo": "horse riding",
    "army": "army soldiers",
    "exército": "army soldiers",
    "exercito": "army soldiers",
    "castle": "medieval castle",
    "castelo": "medieval castle",
    "church": "church building",
    "igreja": "church building",
    "cathedral": "cathedral gothic",
    "catedral": "cathedral gothic",
    "ruins": "ancient ruins",
    "ruina": "ancient ruins",
    "ruína": "ancient ruins",
    "ruinas": "ancient ruins",
    "ruínas": "ancient ruins",
    "forest": "forest nature",
    "floresta": "forest nature",
    "desert": "desert landscape",
    "deserto": "desert landscape",
    "mountains": "mountain landscape",
    "montanha": "mountain landscape",
    "ocean": "ocean sea waves",
    "oceano": "ocean sea waves",
    "city": "city architecture",
    "cidade": "city architecture",
    "map": "world map",
    "mapa": "world map",
}


def _simplify_for_stock(query: str) -> str:
    """
    Traduz query histórica/específica para termos visuais que existem
    no Pexels/Pixabay. Usa mapeamento de temas → queries stock.

    Ex:
      "roman legions barbarian invasion"  -> "ancient rome"
      "roman senate corruption ancient"   -> "ancient rome"
      "ancient egypt pyramid mystery"     -> "ancient egypt"
      "tunguska explosion 1908"           -> "forest fire" (fallback: 2 primeiras palavras)
    """
    query_lower = query.strip().lower()
    if not query_lower:
        return query

    # 1. Tenta mapeamento exato completo (query inteira como chave)
    if query_lower in _HISTORICAL_STOCK_MAP:
        return _HISTORICAL_STOCK_MAP[query_lower]

    # 2. Tenta mapeamento por palavra-chave (qualquer palavra da query)
    words = query.strip().split()
    for word in words:
        word_lower = word.lower().strip(".,!?;:")
        if word_lower in _HISTORICAL_STOCK_MAP:
            return _HISTORICAL_STOCK_MAP[word_lower]

    # 3. Fallback: primeiras 2-3 palavras (corta termos muito longos)
    return " ".join(words[:3]).strip()


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