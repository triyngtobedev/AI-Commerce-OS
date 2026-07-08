def analyze_opportunity(product_analysis, technical_score):
    """
    Analisa potencial de venda combinando:
    - análise da IA
    - métricas reais do produto
    """

    ai_score = product_analysis.get(
        "score",
        0
    )

    market_score = technical_score.get(
        "score",
        0
    )


    final_score = round(
        (ai_score * 0.4) +
        (market_score * 0.6)
    )


    if final_score >= 85:
        decisao = "CRIAR_VIDEO"

    elif final_score >= 70:
        decisao = "TESTAR"

    else:
        decisao = "IGNORAR"


    return {
        "tipo": "afiliado",
        "score_venda": final_score,
        "score_ia": ai_score,
        "score_mercado": market_score,
        "decisao": decisao,

        "facilidade_video": (
            "alta"
            if final_score >= 80
            else "media"
        ),

        "angulos": [
            "Antes e depois",
            "Problema e solução",
            "Produto que você não sabia que precisava"
        ],

        "ganchos": [
            "Eu não sabia que precisava disso até testar...",
            "Esse produto parece inútil, mas olha isso..."
        ]
    }