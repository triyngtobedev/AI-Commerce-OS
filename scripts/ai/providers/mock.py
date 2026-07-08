import json

from scripts.ai.gemini.mock_data import get_mock_content


def generate(prompt, task="analysis"):

    if task == "content":

        return json.dumps(
            {
                "titulo": "Testei esse produto para descobrir se vale a pena",
                "descricao": "Resolvi testar esse produto e mostrar o resultado real.",
                "hashtags": [
                    "#TestandoGadgets",
                    "#Achadinhos"
                ],
                "texto_narracao": "Eu encontrei esse produto e resolvi testar para descobrir se ele realmente entrega o que promete.",
                "duracao": "30 segundos",
                "modo": "review"
            },
            ensure_ascii=False
        )


    if task == "script":

        return json.dumps(
            {
                "hook": "Eu achei que esse produto era só mais um gadget barato, mas resolvi testar.",
                "problema": "Eu queria descobrir se ele realmente ajudava no dia a dia.",
                "teste": "Usei o produto durante alguns dias para ver o resultado.",
                "resultado": "Ele surpreendeu em algumas situações.",
                "cta": "Segue @testandogadgets para mais testes reais."
            },
            ensure_ascii=False
        )


    return json.dumps(
        {
            "score": 90,
            "potencial": "alto",
            "publico_alvo": "Pessoas interessadas no produto",
            "motivos": [
                "Produto visual para vídeos curtos",
                "Resolve um problema comum"
            ]
        },
        ensure_ascii=False
    )