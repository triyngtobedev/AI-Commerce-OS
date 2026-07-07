def generate_script(product, opportunity):
    """
    Gera estrutura de roteiro para vídeo de afiliado.
    """

    nome = product.get("nome", "Produto")

    gancho = opportunity["ganchos"][0]

    roteiro = {
        "produto": nome,

        "titulo": f"Você precisa conhecer esse {nome}",

        "estrutura": {
            "cena_1_hook": gancho,

            "cena_2_problema": (
                "Mostrar o problema que o produto resolve "
                "e criar identificação com o público."
            ),

            "cena_3_demonstracao": (
                "Mostrar o produto funcionando com um "
                "antes e depois visual."
            ),

            "cena_4_cta": (
                "Chamar o público para conferir o produto "
                "através do link."
            )
        }
    }

    return roteiro