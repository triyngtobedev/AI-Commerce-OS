def decide_action(opportunity):
    """
    Decide próxima ação baseada no score.
    """

    score = opportunity.get(
        "score_venda",
        0
    )

    if score >= 90:
        return "CRIAR_VIDEO_AGORA"

    elif score >= 75:
        return "TESTAR_VIDEO"

    else:
        return "DESCARTAR"