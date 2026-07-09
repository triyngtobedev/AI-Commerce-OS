from typing import List, Dict, Any



def extract_score(product: Dict[str, Any]):

    """
    Extrai score comercial do produto.

    Aceita:
    - produto bruto
    - produto com score técnico
    - produto com oportunidade IA
    """



    # =========================
    # OPORTUNIDADE IA
    # =========================

    oportunidade = product.get(
        "oportunidade",
        {}
    )


    if isinstance(
        oportunidade,
        dict
    ):


        score = oportunidade.get(
            "score_venda"
        )


        if score is not None:

            return score



        score = oportunidade.get(
            "score"
        )


        if score is not None:

            return score



    # =========================
    # SCORE TÉCNICO
    # =========================

    tecnico = product.get(
        "score_tecnico",
        {}
    )


    if isinstance(
        tecnico,
        dict
    ):


        score = tecnico.get(
            "score"
        )


        if score is not None:

            return score



    # =========================
    # SCORE DIRETO
    # =========================

    if isinstance(
        product.get("score"),
        (int, float)
    ):

        return product["score"]



    return 0





def rank_products(products: List[Dict[str, Any]]):

    """
    Ordena produtos pelo potencial comercial.

    O maior score fica primeiro.
    """



    ranked = []



    for product in products:


        score = extract_score(
            product
        )



        ranked.append(

            {

                "produto": product,

                "score": score

            }

        )



    ranked.sort(

        key=lambda item: item["score"],

        reverse=True

    )



    return ranked