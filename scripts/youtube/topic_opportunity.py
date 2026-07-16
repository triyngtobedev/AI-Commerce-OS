"""
Opportunity Engine para temas YouTube.

Adapta a lógica de oportunidade do affiliate engine
para avaliar potencial de monetização via AdSense.
"""

from scripts.youtube.topic_scorer import calculate_topic_score


def analyze_topic_opportunity(analysis, topic_score):
    """
    Avalia oportunidade de produção para um tema YouTube.

    Retorna estrutura compatível com o pipeline existente.
    """

    ia_score = analysis.get("score", 50)

    score_venda = round(
        ia_score * 0.5
        + topic_score * 0.5
    )


    if score_venda >= 85:

        decisao = "CRIAR_VIDEO"

    elif score_venda >= 70:

        decisao = "TESTAR"

    else:

        decisao = "IGNORAR"


    angulos = [
        analysis.get(
            "angulo_sugerido",
            topic_score and "documentario"
        )
    ]


    if isinstance(analysis.get("motivos"), list):

        angulos.extend(
            analysis["motivos"][:2]
        )


    ganchos = []

    if analysis.get("gancho"):

        ganchos.append(analysis["gancho"])


    return {
        "tipo": "youtube_adsense",
        "score_venda": score_venda,
        "score_ia": ia_score,
        "score_mercado": topic_score,
        "decisao": decisao,
        "facilidade_video": analysis.get(
            "facilidade_producao",
            "alta"
        ),
        "potencial_watch_time": analysis.get(
            "potencial_watch_time",
            "medio"
        ),
        "disponibilidade_midia": analysis.get(
            "disponibilidade_midia",
            "media"
        ),
        "angulos": angulos,
        "ganchos": ganchos,
    }
