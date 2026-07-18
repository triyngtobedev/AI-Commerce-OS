#!/usr/bin/env python3
"""Testa OPENROUTER_API_KEY diretamente contra a API."""

from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

MODELS = [
    "mistralai/mistral-7b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-3-4b-it:free",
    "microsoft/phi-3-mini-128k-instruct:free",
]

APP_URL = os.getenv(
    "OPENROUTER_APP_URL",
    "https://github.com/triyngtobedev/AI-Commerce-OS",
)
APP_TITLE = os.getenv("OPENROUTER_APP_TITLE", "Vibecoder AI-Commerce-OS")


def test_model(api_key: str, model: str) -> tuple[int, str]:
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": APP_URL,
            "X-OpenRouter-Title": APP_TITLE,
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": "Responda apenas: OK"}],
        },
        timeout=60,
    )
    return response.status_code, response.text[:500]


def main() -> int:
    api_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    if not api_key:
        print("OPENROUTER_API_KEY ausente — configure no .env ou Railway Variables")
        return 1

    print(f"Testando OpenRouter ({len(MODELS)} modelos :free)...\n")

    for model in MODELS:
        status, body = test_model(api_key, model)
        print(f"[{status}] {model}")
        print(body)
        print()

        if status == 200 and "OK" in body.upper():
            print(f"✅ Modelo funcional: {model}")
            return 0

    print("❌ Nenhum modelo :free respondeu com sucesso")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
