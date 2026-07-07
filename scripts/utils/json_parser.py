import json


def parse_json(response):
    """
    Converte resposta JSON da IA em dicionário Python.
    """

    response = response.replace("```json", "")
    response = response.replace("```", "")
    response = response.strip()

    return json.loads(response)