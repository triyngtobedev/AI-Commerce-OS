from scripts.ai.gemini.client import ask_gemini
from scripts.utils.prompt_loader import load_prompt
from scripts.utils.json_parser import parse_json


def generate_content(product, analysis, script):
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

Roteiro:
{script}
"""

    response = ask_gemini(full_prompt)

    content = parse_json(response)

    print("\n========== CONTENT DEBUG ==========")
    print(content)
    print("===================================\n")

    return content