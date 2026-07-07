"""
AI Analyst

Primeira versão do analisador de produtos
do AI-Commerce-OS.

Futuramente será conectado a um modelo
de Inteligência Artificial real.
"""


def analyze_product(product):
    """
    Analisa um produto e gera um score
    baseado nos sinais de engajamento.
    """

    views = product["visualizacoes"]
    likes = product["curtidas"]
    comments = product["comentarios"]

    engagement_rate = ((likes + comments) / views) * 100
    score = round(engagement_rate * 10)

    if score >= 70:
        potential = "alto"
    elif score >= 40:
        potential = "medio"
    else:
        potential = "baixo"


    return {
        "produto": product["nome"],
        "potencial": potential,
        "score": score,
        "engagement_rate": round(engagement_rate, 2)
    }


if __name__ == "__main__":

    produto_teste = {
        "nome": "Mini Aspirador Portátil",
        "visualizacoes": 150000,
        "curtidas": 12000,
        "comentarios": 850
    }

    resultado = analyze_product(produto_teste)

    print(resultado)