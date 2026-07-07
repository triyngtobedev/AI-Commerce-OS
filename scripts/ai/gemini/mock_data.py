def get_mock_content(product_name):
    product = product_name.lower()

    if "aspirador" in product:
        return {
            "titulo": "O mini aspirador que salva seu carro e sua mesa!",
            "descricao": "Pequeno, potente e perfeito para remover sujeiras dos cantinhos difíceis.",
            "hashtags": [
                "#MiniAspirador",
                "#AchadinhosTikTok",
                "#CasaLimpa"
            ],
            "texto_narracao": "Eu achei que era besteira até testar. Esse mini aspirador tira aquela sujeira que fica presa nos lugares mais difíceis.",
            "duracao": "30 segundos"
        }

    if "luminária" in product or "luminaria" in product:
        return {
            "titulo": "A iluminação que mudou meu quarto!",
            "descricao": "Luminária LED inteligente para criar ambientes incríveis com praticidade.",
            "hashtags": [
                "#LuminariaLED",
                "#QuartoDosSonhos",
                "#Achadinhos"
            ],
            "texto_narracao": "Eu não imaginava que uma luz poderia mudar tanto o ambiente. Olha essa transformação.",
            "duracao": "30 segundos"
        }

    return {
        "titulo": "O produto que você precisa conhecer!",
        "descricao": "Produto inovador com potencial para vídeos curtos.",
        "hashtags": [
            "#AchadinhosTikTok"
        ],
        "texto_narracao": "Olha isso que eu encontrei.",
        "duracao": "30 segundos"
    }