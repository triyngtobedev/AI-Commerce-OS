from scripts.ai.tasks.content import generate_content_ai
from scripts.utils.prompt_loader import load_prompt
from scripts.utils.json_parser import parse_json


def generate_content(product, analysis, opportunity, script):
    """
    Gera pacote completo de conteúdo para publicação.
    """

    prompt = load_prompt("content_generation")

    full_prompt = f"""
    TASK: CONTENT_GENERATION
    
{prompt}

Produto:
{product}

Análise:
{analysis}

Oportunidade:
{opportunity}

Roteiro:
{script}
"""

    response = generate_content_ai(full_prompt)

    content = parse_json(response)

    print("\n========== CONTENT DEBUG ==========")
    print(content)
    print("===================================\n")

    return content