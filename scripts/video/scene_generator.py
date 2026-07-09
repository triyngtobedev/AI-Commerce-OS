def generate_scenes(product, content):
    """
    Transforma conteúdo em cenas visuais específicas
    para busca de mídia e geração de legenda.
    """

    nome = product["nome"]


    narracao = content.get(
        "texto_narracao",
        ""
    )


    descricao = content.get(
        "descricao",
        narracao
    )



    scenes = {

        "produto": nome,


        "cenas": [

            {
                "tempo": "0-3",
                "tipo": "hook",
                "visual": (
                    f"person discovering a problem "
                    f"solved by {nome}, "
                    "before and after situation"
                ),
                "narracao": narracao
            },


            {
                "tempo": "3-15",
                "tipo": "demonstracao",
                "visual": (
                    f"person using {nome} "
                    "in real life, "
                    "close up demonstration, "
                    "product in action"
                ),
                "narracao": descricao
            },


            {
                "tempo": "15-25",
                "tipo": "beneficio",
                "visual": (
                    f"clean result after using {nome}, "
                    "happy person showing improvement"
                ),
                "narracao": (
                    "Uma solução simples "
                    "para facilitar o seu dia a dia."
                )
            },


            {
                "tempo": "25-30",
                "tipo": "cta",
                "visual": (
                    f"{nome} product showcase, "
                    "modern commercial style, "
                    "close up"
                ),
                "narracao": (
                    "Clique e garanta o seu."
                )
            }

        ]

    }


    return scenes