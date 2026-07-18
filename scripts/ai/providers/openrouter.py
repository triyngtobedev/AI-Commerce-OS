import os

import requests

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "mistralai/mistral-7b-instruct:free"
OPENROUTER_MODELS_FALLBACK = [
    OPENROUTER_MODEL,
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-3-4b-it:free",
    "microsoft/phi-3-mini-128k-instruct:free",
]
OPENROUTER_APP_URL = os.getenv(
    "OPENROUTER_APP_URL",
    "https://github.com/triyngtobedev/AI-Commerce-OS",
)
OPENROUTER_APP_TITLE = os.getenv("OPENROUTER_APP_TITLE", "Vibecoder AI-Commerce-OS")


def _openrouter_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": OPENROUTER_APP_URL,
        "X-OpenRouter-Title": OPENROUTER_APP_TITLE,
    }


def _generate_with_model(prompt: str, model: str, api_key: str) -> str:
    response = requests.post(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        headers=_openrouter_headers(api_key),
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
    choices = data.get("choices") or []
    if not choices:
        raise Exception(f"OpenRouter resposta sem choices: {str(data)[:500]}")

    message = choices[0].get("message") or {}
    content = message.get("content")

    print(f"[OpenRouter/{model}] response body: {(content or '')[:500]}")

    if not content or not str(content).strip():
        raise Exception("OpenRouter retornou resposta vazia")

    return str(content)


def generate(prompt: str, model: str | None = None) -> str:
    api_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()

    if not api_key:
        raise Exception("OPENROUTER_API_KEY não encontrada.")

    models = [model] if model else OPENROUTER_MODELS_FALLBACK
    last_error: Exception | None = None

    for candidate in models:
        print(f"[OpenRouter] Tentando modelo: {candidate}")
        try:
            return _generate_with_model(prompt, candidate, api_key)
        except Exception as error:
            last_error = error
            print(f"[OpenRouter/{candidate}] {error}")

    raise last_error or Exception("OpenRouter: nenhum modelo disponível")
