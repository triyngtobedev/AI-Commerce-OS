import os
from google import genai


def generate(prompt, model="gemini-2.0-flash"):

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise Exception("GEMINI_API_KEY não encontrada.")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model,
        contents=prompt
    )

    return response.text