"""
Creative Strategy Engine para YouTube.

Gera estratégia criativa via IA com fallback rule-based.
"""

from scripts.ai.router import ask_ai
from scripts.utils.prompt_loader import load_prompt
from scripts.utils.json_parser import parse_json
from scripts.utils.ai_cache import load_cache, save_cache
from scripts.core.platform_config import YOUTUBE_DARK

CACHE_PREFIX = "youtube"


def generate_youtube_strategy(
    topic,
    analysis,
    opportunity,
):
    """
    Gera estratégia criativa para vídeo YouTube documentário.
    """

    topic_name = topic["nome"]

    print(
        f"🎬 Estratégia YouTube: {topic_name}"
    )


    cached = load_cache(
        "strategy",
        topic_name,
        prefix=CACHE_PREFIX,
    )

    if cached:

        print(
            f"♻️ Cache de estratégia: {topic_name}"
        )

        return cached


    prompt = load_prompt(
        "creative_strategy",
        platform="youtube",
    )


    full_prompt = f"""
TASK: YOUTUBE_CREATIVE_STRATEGY

{prompt}

Tema:
{topic}

Análise:
{analysis}

Oportunidade:
{opportunity}
"""


    response = ask_ai(
        full_prompt,
        "script",
    )


    strategy = parse_json(response)


    if not isinstance(strategy, dict):

        strategy = _fallback_strategy(topic, opportunity)


    strategy.setdefault(
        "schema_version",
        "1.1"
    )

    strategy.setdefault(
        "formato",
        YOUTUBE_DARK.formato
    )

    strategy.setdefault(
        "produto",
        topic_name
    )


    save_cache(
        "strategy",
        topic_name,
        strategy,
        prefix=CACHE_PREFIX,
    )


    return strategy



def _fallback_strategy(topic, opportunity):

    keywords = topic.get("keywords", ["history documentary"])

    queries = []

    for i in range(8):

        kw = keywords[i % len(keywords)] if keywords else "history"

        queries.append(
            f"{kw} historical documentary"
        )


    return {
        "schema_version": "1.1",
        "produto": topic.get("nome", ""),
        "angulo": topic.get(
            "angulo_sugerido",
            "revelacao_historica"
        ),
        "gancho": (
            opportunity.get("ganchos", [""])[0]
            if opportunity.get("ganchos")
            else f"Você não vai acreditar na história de {topic.get('nome', '')}"
        ),
        "estilo_video": "documentario_narrado",
        "cta": YOUTUBE_DARK.cta_template,
        "objetivo": "maximizar watch time",
        "formato": YOUTUBE_DARK.formato,
        "queries_contexto": queries,
        "duracao_alvo": "8 minutos",
        "tom_narracao": "documentario_envolvente",
    }
