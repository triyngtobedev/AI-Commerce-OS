import json

from scripts.utils.prompt_loader import load_prompt
from scripts.ai.gemini.client import ask_gemini
from scripts.utils.json_parser import parse_json


def analyze_product(product):
    """
    Analisa um produto usando Gemini.
    """

    base_prompt = load_prompt(
        "product_analysis"
    )

    product_data = json.dumps(
        product,
        ensure_ascii=False,
        indent=2
    )

    final_prompt = f"""
{base_prompt}

Analise este produto:

{product_data}
"""

    response = ask_gemini(final_prompt)

    analysis = parse_json(response)

    return analysis