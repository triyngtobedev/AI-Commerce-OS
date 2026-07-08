import os
import requests


def search_pexels(query):

    api_key = os.getenv(
        "PEXELS_API_KEY"
    )

    if not api_key:
        return {
            "erro": "PEXELS_API_KEY não encontrada"
        }


    response = requests.get(
        "https://api.pexels.com/v1/search",
        headers={
            "Authorization": api_key
        },
        params={
            "query": query,
            "per_page": 3
        }
    )


    return response.json()