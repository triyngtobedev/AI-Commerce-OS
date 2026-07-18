import os

import requests

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "mistralai/mistral-7b-instruct:free"


def generate(prompt: str, model: str = OPENROUTER_MODEL) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise Exception("OPENROUTER_API_KEY não encontrada.")

    response = requests.post(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )

    if not response.ok:
        raise Exception(
            f"OpenRouter HTTP {response.status_code}: {response.text[:500]}"
        )

    data = response.json()
    content = data["choices"][0]["message"]["content"]

    print(f"[OpenRouter/{model}] response body: {(content or '')[:500]}")

    if not content or not content.strip():
        raise Exception("OpenRouter retornou resposta vazia")

    return content
