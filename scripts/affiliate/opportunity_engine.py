def analyze_opportunity(product_analysis):
    """
    Analisa o potencial de um produto para afiliado.
    """

    score = product_analysis.get("score", 0)

    if score >= 85:
        decisao = "CRIAR_VIDEO"

    elif score >= 70:
        decisao = "TESTAR"

    else:
        decisao = "IGNORAR"

    return {
        "tipo": "afiliado",
        "score_venda": score,
        "decisao": decisao,
        "facilidade_video": "alta" if score >= 80 else "media",
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