"""
Topic Research Engine

Pesquisa e gera pautas automaticamente para o canal YouTube Dark.
Utiliza IA para descobrir temas com alto potencial de monetização
e compatibilidade com produção automatizada.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

from scripts.ai.router import ask_ai
from scripts.utils.prompt_loader import load_prompt
from scripts.utils.json_parser import parse_json
from scripts.utils.ai_cache import load_cache, save_cache
from scripts.core.content_subject import normalize_subject

load_dotenv()

logger = logging.getLogger(__name__)

TOPICS_FILE = Path("database/topics_source.json")
CACHE_PREFIX = "youtube"
LLM_CANDIDATE_COUNT = 10

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
BIG_VIDEO_VIEW_THRESHOLD = 100_000

STATUS_ORDER = {
    "aprovado": 0,
    "inexplorado": 1,
    "saturado": 2,
}


def _get_youtube_api_key() -> Optional[str]:
    """Retorna a chave da YouTube Data API (.env.example não define nome fixo)."""
    for name in ("YOUTUBE_DATA_API_KEY", "YOUTUBE_API_KEY"):
        value = os.getenv(name, "").strip()
        if value:
            return value
    return None


def _classify_competition(big_video_count: int) -> str:
    if big_video_count == 0:
        return "inexplorado"
    if big_video_count <= 5:
        return "aprovado"
    return "saturado"


def _fetch_video_view_counts(api_key: str, video_ids: List[str]) -> List[int]:
    if not video_ids:
        return []

    response = requests.get(
        YOUTUBE_VIDEOS_URL,
        params={
            "part": "statistics",
            "id": ",".join(video_ids),
            "key": api_key,
        },
        timeout=15,
    )
    response.raise_for_status()

    view_counts = []
    for item in response.json().get("items", []):
        raw_count = item.get("statistics", {}).get("viewCount", "0")
        try:
            view_counts.append(int(raw_count))
        except (TypeError, ValueError):
            view_counts.append(0)

    return view_counts


def _validate_topic_youtube(topic: Dict[str, Any], api_key: str) -> str:
    query = str(topic.get("query_youtube", "")).strip()
    if not query:
        query = str(topic.get("nome", "")).strip()

    search_response = requests.get(
        YOUTUBE_SEARCH_URL,
        params={
            "part": "snippet",
            "q": query,
            "type": "video",
            "relevanceLanguage": "pt",
            "regionCode": "BR",
            "maxResults": 5,
            "key": api_key,
        },
        timeout=15,
    )
    search_response.raise_for_status()

    video_ids = [
        item["id"]["videoId"]
        for item in search_response.json().get("items", [])
        if item.get("id", {}).get("videoId")
    ]

    view_counts = _fetch_video_view_counts(api_key, video_ids)
    big_video_count = sum(
        1 for count in view_counts if count > BIG_VIDEO_VIEW_THRESHOLD
    )

    return _classify_competition(big_video_count)


def validate_topics_youtube(topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Valida concorrência no YouTube BR via Data API v3.

    Adiciona status_concorrencia e ordena: aprovado → inexplorado → saturado.
    Em falha de API ou chave ausente, retorna a lista original sem alterações.
    """
    api_key = _get_youtube_api_key()
    if not api_key:
        logger.warning(
            "YOUTUBE_DATA_API_KEY/YOUTUBE_API_KEY ausente — "
            "salvando temas sem validação de concorrência."
        )
        return topics

    validated: List[Dict[str, Any]] = []

    try:
        for topic in topics:
            enriched = dict(topic)
            enriched["status_concorrencia"] = _validate_topic_youtube(
                enriched,
                api_key,
            )
            validated.append(enriched)
    except requests.RequestException as exc:
        logger.warning(
            "Falha na validação YouTube (%s) — salvando temas sem validação.",
            exc,
        )
        return topics
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning(
            "Resposta inesperada da YouTube API (%s) — salvando sem validação.",
            exc,
        )
        return topics

    validated.sort(
        key=lambda item: STATUS_ORDER.get(
            item.get("status_concorrencia", "saturado"),
            99,
        )
    )

    return validated


def research_topics(
    niche: str = "historia_curiosidades",
    count: int = 5,
    save: bool = True,
) -> List[Dict[str, Any]]:
    """
    Gera pautas automaticamente via IA.

    Args:
        niche: Nicho alvo do canal
        count: Quantidade de temas a gerar
        save: Se True, salva em topics_source.json

    Returns:
        Lista de temas normalizados
    """

    cache_key = f"{niche}_{count}"

    cached = load_cache(
        "topic_research",
        cache_key,
        prefix=CACHE_PREFIX,
    )

    if cached:

        print(
            f"♻️ Cache de pesquisa de temas: {niche}"
        )

        return [
            normalize_subject(t, content_type="topic")
            for t in cached
        ]


    print(
        f"🔍 Pesquisando {count} temas para nicho: {niche}"
    )


    prompt = load_prompt(
        "topic_research",
        platform="youtube",
    )


    full_prompt = f"""
TASK: TOPIC_RESEARCH

{prompt}

Nicho: {niche}
Quantidade de temas: {LLM_CANDIDATE_COUNT}
"""


    response = ask_ai(
        full_prompt,
        "analysis",
    )


    parsed = parse_json(response)


    if not isinstance(parsed, list):

        if isinstance(parsed, dict):

            parsed = parsed.get(
                "topics",
                parsed.get("temas", [])
            )

        else:

            parsed = []


    candidates: List[Dict[str, Any]] = []

    for item in parsed[:LLM_CANDIDATE_COUNT]:

        if not isinstance(item, dict):

            continue


        try:

            candidates.append(
                normalize_subject(
                    item,
                    content_type="topic",
                )
            )

        except ValueError:

            continue


    validated = validate_topics_youtube(candidates)
    topics = validated[:count]


    if topics:

        save_cache(
            "topic_research",
            cache_key,
            [dict(t) for t in topics],
            prefix=CACHE_PREFIX,
        )


    if save and topics:

        _merge_topics_file(topics)


    print(
        f"✅ {len(topics)} tema(s) pesquisado(s)"
    )


    return topics



def _merge_topics_file(new_topics: List[Dict[str, Any]]):
    """
    Mescla novos temas em topics_source.json
    evitando duplicatas por nome.
    """

    existing = []

    if TOPICS_FILE.exists():

        with open(
            TOPICS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)


        existing = (
            data
            if isinstance(data, list)
            else data.get("topics", [])
        )


    existing_names = {
        t.get("nome", "").lower()
        for t in existing
    }


    for topic in new_topics:

        name = topic.get("nome", "").lower()

        if name and name not in existing_names:

            clean = {
                k: v
                for k, v in topic.items()
                if not k.startswith("_")
            }

            existing.append(clean)

            existing_names.add(name)


    TOPICS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    with open(
        TOPICS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            existing,
            file,
            ensure_ascii=False,
            indent=4,
        )


    print(
        f"💾 Temas salvos em {TOPICS_FILE}"
    )
