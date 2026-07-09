def generate_scenes(product, content):
    """
    Transforma conteúdo em cenas visuais específicas para busca de mídia.
    """

    nome = product["nome"]

    scenes = {
        "produto": nome,
        "cenas": [
            {
                "tempo": "0-3s",
                "tipo": "hook",
                "visual": f"person discovering dirty problem solved by {nome}, before and after situation",
                "narracao": content["texto_narracao"]
            },
            {
                "tempo": "3-15s",
                "tipo": "demonstracao",
                "visual": f"person using {nome} in real life, close up demonstration, product in action",
                "narracao": content["descricao"]
            },
            {
                "tempo": "15-25s",
                "tipo": "beneficio",
                "visual": f"clean result after using {nome}, happy person showing improvement",
                "narracao": "Uma solução simples para o seu dia a dia."
            },
            {
                "tempo": "25-30s",
                "tipo": "cta",
                "visual": f"{nome} product showcase, modern commercial style, close up",
                "narracao": "Clique e garanta o seu."
            }
        ]
    }

    return scenes