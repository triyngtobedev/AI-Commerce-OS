import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


ROOT_DIR = Path(__file__).resolve().parents[3]

load_dotenv(ROOT_DIR / ".env")


def get_gemini_client():
    """
    Cria cliente do Gemini.
    """

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise Exception("GEMINI_API_KEY não encontrada.")

    client = genai.Client(api_key=api_key)

    return client


def ask_gemini(prompt):
    """
    Envia um prompt para o Gemini
    e retorna a resposta.
    """

    client = get_gemini_client()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text