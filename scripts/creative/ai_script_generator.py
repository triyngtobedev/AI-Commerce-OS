from scripts.ai.gemini.client import ask_gemini
from scripts.utils.prompt_loader import load_prompt
from scripts.utils.json_parser import parse_json


def generate_ai_script(product, analysis):
    """
    Gera roteiro de vídeo usando Gemini.
    """

    prompt = load_prompt("video_script")

    full_prompt = f"""
{prompt}

Produto:
{product}

Análise:
{analysis}
"""

    response = ask_gemini(full_prompt)

    return parse_json(response)