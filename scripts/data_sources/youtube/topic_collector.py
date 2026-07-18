"""
Coletor de temas para pipeline YouTube.

Lê temas de database/topics_source.json.
Futuramente pode integrar com APIs de tendências.
"""

import json
import os
from pathlib import Path

from scripts.core.content_subject import normalize_subject

TOPICS_FILE = Path("database/topics_source.json")


def collect_topics():
    """
    Carrega temas disponíveis para produção de vídeo.

    Retorna lista de sujeitos normalizados (content_type=topic).
    """

    override = os.getenv("PIPELINE_TOPIC_OVERRIDE")
    if override:
        print(f"🔥 Tema injetado pelo n8n: {override}")
        return [normalize_subject({"nome": override, "categoria": "historia"}, content_type="topic")]

    if not TOPICS_FILE.exists():

        print(
            f"⚠️ Arquivo de temas não encontrado: {TOPICS_FILE}"
        )

        return []


    with open(
        TOPICS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)


    topics = data if isinstance(data, list) else data.get("topics", [])


    normalized = []

    for topic in topics:

        try:

            normalized.append(
                normalize_subject(
                    topic,
                    content_type="topic"
                )
            )

        except ValueError as error:

            print(
                f"⚠️ Tema inválido ignorado: {error}"
            )


    print(
        f"📚 {len(normalized)} tema(s) carregado(s)"
    )


    return normalized
