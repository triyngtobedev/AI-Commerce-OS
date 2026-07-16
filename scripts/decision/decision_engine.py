def decide_action(opportunity):
    """
    Decide próxima ação baseada no score.
    Alinhado com opportunity_engine.decisao.
    """

    score = opportunity.get(
        "score_venda",
        0
    )

    if score >= 85:
        return "CRIAR_VIDEO_AGORA"

    elif score >= 70:
        return "TESTAR_VIDEO"

    else:
        return "DESCARTAR"