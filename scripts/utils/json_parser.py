import json


def parse_json_response(response):
    """
    Converte resposta da IA em objeto Python.
    """

    cleaned_response = response.strip()

    # Remove blocos markdown caso a IA retorne ```json
    if cleaned_response.startswith("```"):
        cleaned_response = (
            cleaned_response
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

    return json.loads(cleaned_response)