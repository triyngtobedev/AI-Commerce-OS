"""
Topic Research Engine

Pesquisa e gera pautas automaticamente para o canal YouTube Dark.
Utiliza IA para descobrir temas com alto potencial de monetização
e compatibilidade com produção automatizada.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from scripts.ai.router import ask_ai
from scripts.utils.prompt_loader import load_prompt
from scripts.utils.json_parser import parse_json
from scripts.utils.ai_cache import load_cache, save_cache
from scripts.core.content_subject import normalize_subject

TOPICS_FILE = Path("database/topics_source.json")
CACHE_PREFIX = "youtube"


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
Quantidade de temas: {count}
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


    topics = []

    for item in parsed[:count]:

        if not isinstance(item, dict):

            continue


        try:

            topics.append(
                normalize_subject(
                    item,
                    content_type="topic",
                )
            )

        except ValueError:

            continue


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
