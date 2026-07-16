"""
Analista de temas para pipeline YouTube.

Reutiliza a infraestrutura de IA do ai_analyst,
com prompt específico para temas históricos.
"""

from scripts.ai.router import ask_ai
from scripts.utils.prompt_loader import load_prompt
from scripts.utils.json_parser import parse_json
from scripts.utils.ai_cache import load_cache, save_cache

CACHE_PREFIX = "youtube"


def analyze_topic(topic):
    """
    Analisa potencial de um tema para produção YouTube.
    """

    topic_name = topic["nome"]

    print(
        f"🔎 Analisando tema: {topic_name}"
    )


    cached = load_cache(
        "analysis",
        topic_name,
        prefix=CACHE_PREFIX,
    )

    if cached:

        print(
            f"♻️ Cache de análise: {topic_name}"
        )

        return cached


    prompt = load_prompt(
        "topic_analysis",
        platform="youtube",
    )


    full_prompt = f"""
TASK: TOPIC_ANALYSIS

{prompt}

Tema:
{topic}
"""


    response = ask_ai(
        full_prompt,
        "analysis",
    )


    analysis = parse_json(response)


    if not isinstance(analysis, dict):

        analysis = _fallback_analysis(topic)


    save_cache(
        "analysis",
        topic_name,
        analysis,
        prefix=CACHE_PREFIX,
    )


    return analysis



def _fallback_analysis(topic):

    return {
        "score": 70,
        "potencial": "medio",
        "publico_alvo": "Interessados em história e curiosidades",
        "motivos": [
            f"Tema '{topic.get('nome', '')}' tem apelo educativo",
            "Produção automatizada viável",
        ],
        "facilidade_producao": "alta",
        "potencial_watch_time": "medio",
        "disponibilidade_midia": "media",
        "risco_conteudo": "baixo",
    }
