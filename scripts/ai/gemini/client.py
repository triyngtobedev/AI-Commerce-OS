import os
import json
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from .mock_data import get_mock_content


ROOT_DIR = Path(__file__).resolve().parents[3]

load_dotenv(ROOT_DIR / ".env")


def get_gemini_client():

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise Exception("GEMINI_API_KEY não encontrada.")

    client = genai.Client(api_key=api_key)

    return client


def extract_product_name(prompt):
    """
    Extrai nome do produto do prompt.
    """

    lines = prompt.split("\n")

    for line in lines:
        if "Produto:" in line:
            return line.replace("Produto:", "").strip()

    return "produto"


def ask_gemini(prompt):
    """
    Envia um prompt para o Gemini
    ou usa resposta simulada em desenvolvimento.
    """

    mode = os.getenv(
        "GEMINI_MODE",
        "mock"
    )

    if mode == "mock":

        print("\nPROMPT RECEBIDO:")
        print(prompt[:300])
        print("\n")

        if "task: content_generation" in prompt.lower():

            product_name = extract_product_name(prompt)

            return json.dumps(
                get_mock_content(product_name),
                ensure_ascii=False,
                indent=4
            )

        if "video_script" in prompt.lower():

            return """
            {
                "hook": "Eu não sabia que precisava disso até testar...",
                "problema": "Sujeiras pequenas em lugares difíceis de limpar.",
                "demonstracao": "Mostra o produto funcionando.",
                "beneficio": "Limpeza rápida e prática.",
                "cta": "Clique no link e garanta o seu."
            }
            """

        return """
        {
            "score": 90,
            "potencial": "alto",
            "publico_alvo": "Pessoas interessadas no produto",
            "motivos": [
                "Produto visual para vídeos curtos",
                "Resolve um problema comum"
            ]
        }
        """

    client = get_gemini_client()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text