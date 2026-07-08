from scripts.ai.gemini.client import ask_gemini
from scripts.utils.prompt_loader import load_prompt
from scripts.utils.json_parser import parse_json


def generate_ai_script(
    product, 
    analysis,
    opportunity
    ):
    """
    Gera roteiro de vídeo usando Gemini.
    """

    prompt = load_prompt("review_script")

    full_prompt = f"""
    TASK: REVIEW_SCRIPT
    
{prompt}

Produto:
{product}

Análise:
{analysis}

Oportunidade:
{opportunity}
"""

    response = ask_gemini(full_prompt)

    return parse_json(response)