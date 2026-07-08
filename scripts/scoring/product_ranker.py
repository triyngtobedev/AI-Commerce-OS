def rank_products(products):
    """
    Ordena produtos pelo score.
    Aceita produtos crus ou analisados.
    """

    ranked = []


    for product in products:

        # Produto já analisado
        if "produto" in product:

            score = product.get(
                "oportunidade",
                {}
            ).get(
                "score_venda",
                0
            )

        # Produto bruto
        else:

            score = product.get(
                "score_tecnico",
                {}
            ).get(
                "score",
                0
            )


        ranked.append(
            {
                "produto": product,
                "score": score
            }
        )


    ranked.sort(
        key=lambda x: x["score"],
        reverse=True
    )


    return ranked