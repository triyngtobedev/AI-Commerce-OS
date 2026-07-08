def get_mock_content(product_name):
    product = product_name.lower()

    if "aspirador" in product:
        return {
            "titulo": "Eu achei que esse mini aspirador era inútil... até testar",
            "descricao": "Resolvi testar esse gadget para descobrir se ele realmente consegue ajudar nas pequenas sujeiras do dia a dia.",
            "hashtags": [
                "#TestandoGadgets",
                "#Achadinhos",
                "#Tecnologia"
            ],
            "texto_narracao": "Eu sempre tinha aquelas sujeiras pequenas no carro e na mesa que davam trabalho para tirar. Vi esse mini aspirador e resolvi testar. Pelo tamanho eu não esperava muito, mas ele conseguiu resolver algumas situações bem específicas.",
            "duracao": "30 segundos",
            "modo": "review"
        }

    if "luminária" in product or "luminaria" in product:
        return {
            "titulo": "Testei essa luminária barata para ver se realmente muda o ambiente",
            "descricao": "Será que uma luminária simples consegue transformar um quarto? Resolvi testar na prática.",
            "hashtags": [
                "#TestandoGadgets",
                "#Setup",
                "#Achadinhos"
            ],
            "texto_narracao": "Eu achava que era só uma luz bonita, mas resolvi testar como ficaria no ambiente. O resultado foi uma mudança simples, mas que faz diferença principalmente à noite.",
            "duracao": "30 segundos",
            "modo": "review"
        }

    return {
        "titulo": "Testei esse produto para descobrir se vale a pena",
        "descricao": "Resolvi testar esse produto e mostrar o resultado real.",
        "hashtags": [
            "#TestandoGadgets",
            "#Achadinhos"
        ],
        "texto_narracao": "Eu encontrei esse produto e resolvi testar para descobrir se ele realmente entrega o que promete.",
        "duracao": "30 segundos",
        "modo": "review"
    }