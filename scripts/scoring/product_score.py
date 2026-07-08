def calculate_product_score(product):
    """
    Calcula score inicial do produto baseado em métricas reais.
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


    # Taxas de engajamento

    like_rate = (
        likes / views
        if views > 0
        else 0
    )

    comment_rate = (
        comments / views
        if views > 0
        else 0
    )


    score = 0


    # Alcance

    if views >= 100000:
        score += 30

    elif views >= 50000:
        score += 20

    else:
        score += 10


    # Curtidas

    if like_rate >= 0.08:
        score += 25

    elif like_rate >= 0.05:
        score += 15


    # Comentários (interesse real)

    if comment_rate >= 0.005:
        score += 20

    elif comment_rate >= 0.002:
        score += 10


    # Preço para compra por impulso

    if 30 <= price <= 150:
        score += 25


    return {
        "score": score,
        "engagement": round(
            like_rate * 100,
            2
        ),
        "comment_rate": round(
            comment_rate * 100,
            3
        )
    }