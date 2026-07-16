"""
Scoring de temas para pipeline YouTube.

Avalia potencial de monetização e facilidade de produção
sem depender de métricas de TikTok (views, likes).
"""

POTENCIAL_SCORES = {
    "alto": 90,
    "medio": 65,
    "baixa": 40,
    "baixo": 40,
}

DIFICULDADE_SCORES = {
    "baixa": 90,
    "media": 65,
    "alta": 40,
}


def calculate_topic_score(topic, analysis=None):
    """
    Calcula score técnico de um tema (0-100).

    Combina metadados do tema com análise de IA quando disponível.
    """

    score = 50


    potencial = topic.get(
        "potencial_monetizacao",
        "medio"
    ).lower()

    score += (
        POTENCIAL_SCORES.get(potencial, 65) * 0.3
    )


    dificuldade = topic.get(
        "dificuldade_pesquisa",
        "media"
    ).lower()

    score += (
        DIFICULDADE_SCORES.get(dificuldade, 65) * 0.2
    )


    keywords = topic.get("keywords", [])

    if len(keywords) >= 3:

        score += 10


    if analysis:

        ia_score = analysis.get("score", 50)

        score = (
            score * 0.4
            + ia_score * 0.6
        )


    return min(100, max(0, round(score)))



def rank_topics(topics_with_scores):
    """
    Ordena temas por score decrescente.

    Args:
        topics_with_scores: lista de dicts com 'produto' e 'score'

    Returns:
        Lista ordenada
    """

    return sorted(
        topics_with_scores,
        key=lambda x: x.get("score", 0),
        reverse=True,
    )
