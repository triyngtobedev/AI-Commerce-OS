from scripts.ai.router import ask_ai
from scripts.utils.prompt_loader import load_prompt
from scripts.utils.json_parser import parse_json
from scripts.utils.ai_cache import load_cache, save_cache


def generate_content(
    product,
    analysis,
    opportunity,
    script
):
    """
    Gera conteúdo com cache.
    """

    product_name = product["nome"]


    cached = load_cache(
        "content",
        product_name
    )


    if cached and "texto_narracao" in cached:

        print(
            f"♻️ Conteúdo em cache: {product_name}"
        )

        return cached



    print(
        f"📝 Gerando conteúdo: {product_name}"
    )


    prompt = load_prompt(
        "content_generation"
    )


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


    response = ask_ai(
        full_prompt,
        "content",
    )


    content = parse_json(
        response
    )


    save_cache(
        "content",
        product_name,
        content
    )

    print("\n========== CONTENT GERADO ==========")
    print(content)
    print("====================================\n")


    return content