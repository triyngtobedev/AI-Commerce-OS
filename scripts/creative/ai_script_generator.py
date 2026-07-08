from scripts.ai.tasks.script import generate_script
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

    response = generate_script(full_prompt)

    return parse_json(response)