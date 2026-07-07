import json


def generate_scenes(product, content):
    """
    Transforma conteúdo em cenas de vídeo.
    """

    scenes = {
        "produto": product["nome"],
        "cenas": [
            {
                "tempo": "0-3s",
                "tipo": "hook",
                "visual": f"Mostrar o problema resolvido pelo {product['nome']}",
                "narracao": content["texto_narracao"]
            },
            {
                "tempo": "3-15s",
                "tipo": "demonstracao",
                "visual": f"Mostrar o {product['nome']} funcionando",
                "narracao": content["descricao"]
            },
            {
                "tempo": "15-25s",
                "tipo": "beneficio",
                "visual": "Mostrar resultado final",
                "narracao": "Uma solução simples para o seu dia a dia."
            },
            {
                "tempo": "25-30s",
                "tipo": "cta",
                "visual": "Produto em destaque",
                "narracao": "Clique e garanta o seu."
            }
        ]
    }

    return scenes