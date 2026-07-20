from scripts.ai.router import ask_ai
import os
import json
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from .mock_data import get_mock_content


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


def extract_product_name(prompt):
    """
    Extrai nome do produto do prompt.
    """

    lines = prompt.split("\n")

    for line in lines:
        if "Produto:" in line:
            return line.replace("Produto:", "").strip()

    return "produto"


def _infer_context_type(prompt: str) -> str:
    prompt_lower = prompt.lower()

    if "script_rewrite" in prompt_lower or "review_script" in prompt_lower:
        return "script_rewrite"
    if "script_expansion" in prompt_lower:
        return "script_expansion"
    if any(
        token in prompt_lower
        for token in ("video_script", "script_generation", "roteiro", "task: script")
    ):
        return "script_generation"
    if "task: content_generation" in prompt_lower or "content_generation" in prompt_lower:
        return "content_generation"
    if "task: strategy" in prompt_lower or "strategy" in prompt_lower:
        return "strategy"
    if "task: analysis" in prompt_lower or "analysis" in prompt_lower:
        return "analysis"

    return "default"


def ask_gemini(prompt, context_type=None):
    """
    Envia um prompt para o router de IA (Groq → OpenRouter)
    ou usa resposta simulada em desenvolvimento.
    """

    mode = os.getenv(
        "GEMINI_MODE",
        "api"
    )

    if mode == "mock":

        print("\nPROMPT RECEBIDO:")
        print(prompt[:300])
        print("\n")

        prompt_lower = prompt.lower()

        if "task: content_generation" in prompt_lower:

            product_name = extract_product_name(prompt)

            return json.dumps(
                get_mock_content(product_name),
                ensure_ascii=False,
                indent=4
            )


        if "task: review_script" in prompt_lower or "review_script" in prompt_lower:

            return """
            {
                "hook": "Eu achei que esse produto era só mais um gadget barato, mas resolvi testar.",
                "problema": "Eu queria descobrir se ele realmente ajudava no dia a dia.",
                "teste": "Usei o produto durante alguns dias para ver o resultado.",
                "resultado": "Ele surpreendeu em algumas situações e mostrou seus limites.",
                "cta": "Segue @testandogadgets para mais testes reais."
            }
            """


        if "video_script" in prompt_lower:

            return """
            {
                "hook": "Eu não sabia que precisava disso até testar...",
                "problema": "Eu sempre tinha sujeira pequena no teclado, carro e mesa.",
                "teste": "Resolvi testar esse produto por alguns dias.",
                "resultado": "Me surpreendeu pelo tamanho e praticidade.",
                "cta": "Segue @testandogadgets para ver mais testes reais."
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

    resolved_context = context_type or _infer_context_type(prompt)
    return ask_ai(prompt, resolved_context)
