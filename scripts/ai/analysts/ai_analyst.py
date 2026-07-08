import json

from scripts.utils.prompt_loader import load_prompt
from scripts.ai.router import ask_ai
from scripts.utils.json_parser import parse_json
from scripts.utils.ai_cache import load_cache, save_cache


def analyze_product(product):
    """
    Analisa um produto usando IA com sistema de cache.
    """

    product_name = product["nome"]


    # Verifica cache

    cached = load_cache(
        "analysis",
        product_name
    )

    if cached:

        print(
            f"♻️ Cache encontrado: {product_name}"
        )

        return cached



    print(
        f"🤖 Analisando com IA: {product_name}"
    )



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


    response = ask_ai(
        final_prompt,
        "analysis",
    )


    analysis = parse_json(
        response
    )


    # Salva resultado

    save_cache(
        "analysis",
        product_name,
        analysis
    )


    return analysis