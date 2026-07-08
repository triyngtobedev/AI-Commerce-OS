def rank_products(products):

    """
    Ordena produtos pelo potencial de oportunidade.
    """

    ranked = sorted(
        products,
        key=lambda x: x["oportunidade"]["score_venda"],
        reverse=True
    )

    return ranked