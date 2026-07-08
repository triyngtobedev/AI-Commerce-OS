from scripts.ai.router import ask_ai
from scripts.utils.prompt_loader import load_prompt
from scripts.utils.json_parser import parse_json
from scripts.utils.ai_cache import load_cache, save_cache


def generate_ai_script(
    product,
    analysis,
    opportunity
):
    """
    Gera roteiro de vídeo usando IA com cache.
    """

    product_name = product["nome"]


    cached = load_cache(
        "scripts",
        product_name
    )


    if cached:

        print(
            f"♻️ Roteiro em cache: {product_name}"
        )

        return cached



    print(
        f"✍️ Gerando roteiro: {product_name}"
    )


    prompt = load_prompt(
        "review_script"
    )


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


    response = ask_ai(
        full_prompt,
        "script"
    )


    script = parse_json(
        response
    )


    save_cache(
        "scripts",
        product_name,
        script
    )


    return script