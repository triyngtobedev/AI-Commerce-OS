from typing import Dict, Any



def safe_rate(value, total):

    if total <= 0:

        return 0

    return value / total



def calculate_product_score(product: Dict[str, Any]):

    """
    Calcula potencial comercial do produto.

    Avalia:
    - alcance
    - engajamento
    - interesse real
    - preço
    - potencial de compra por impulso
    - facilidade de demonstração
    """



    views = product.get(
        "visualizacoes",
        0
    )


    likes = product.get(
        "curtidas",
        0
    )


    comments = product.get(
        "comentarios",
        0
    )


    price = product.get(
        "preco_estimado",
        0
    )


    category = product.get(
        "categoria",
        ""
    ).lower()



    like_rate = safe_rate(
        likes,
        views
    )


    comment_rate = safe_rate(
        comments,
        views
    )



    score = 0



    factors = {}



    # =========================
    # ALCANCE
    # =========================


    if views >= 500000:

        score += 25

        factors["alcance"] = 25


    elif views >= 100000:

        score += 20

        factors["alcance"] = 20


    elif views >= 50000:

        score += 15

        factors["alcance"] = 15


    else:

        score += 5

        factors["alcance"] = 5



    # =========================
    # ENGAJAMENTO
    # =========================


    if like_rate >= 0.10:

        score += 20

        factors["likes"] = 20


    elif like_rate >= 0.05:

        score += 15

        factors["likes"] = 15


    else:

        factors["likes"] = 5



    # =========================
    # INTENÇÃO DE COMPRA
    # =========================


    if comment_rate >= 0.01:

        score += 20

        factors["comentarios"] = 20


    elif comment_rate >= 0.003:

        score += 10

        factors["comentarios"] = 10


    else:

        factors["comentarios"] = 0



    # =========================
    # PREÇO IMPULSIVO
    # =========================


    if 30 <= price <= 200:

        score += 15

        factors["preco"] = 15


    elif price < 30:

        score += 10

        factors["preco"] = 10


    else:

        factors["preco"] = 0



    # =========================
    # POTENCIAL VISUAL
    # =========================


    visual_categories = [

        "gadgets",

        "tecnologia",

        "casa",

        "utilidade",

        "beleza",

        "pet"

    ]



    if category in visual_categories:

        score += 20

        factors["demonstracao"] = 20


    else:

        factors["demonstracao"] = 5



    # limite máximo

    score = min(
        score,
        100
    )



    return {

        "score": score,


        "engagement": round(
            like_rate * 100,
            2
        ),


        "comment_rate": round(
            comment_rate * 100,
            3
        ),


        "factors": factors,


        "classificacao":

            (
                "Excelente"
                if score >= 80

                else

                "Bom"
                if score >= 60

                else

                "Baixo potencial"
            )

    }