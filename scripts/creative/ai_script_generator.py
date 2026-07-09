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

    Retorna o roteiro que será usado
    pelo gerador de conteúdo.
    """


    product_name = product["nome"]



    # ===============================
    # CACHE
    # ===============================

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



    # ===============================
    # PROMPT
    # ===============================

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



    # ===============================
    # IA
    # ===============================

    response = ask_ai(
        full_prompt,
        "script"
    )



    # ===============================
    # JSON
    # ===============================

    script = parse_json(
        response
    )



    if not isinstance(script, dict):

        print(
            "⚠️ Roteiro inválido retornado pela IA."
        )

        script = {}



    # ===============================
    # GARANTIA DE CONTEÚDO
    # ===============================

    if not script:


        script = {

            "gancho": (
                f"Você precisa conhecer o {product_name}."
            ),

            "roteiro": (
                f"Apresentação do produto {product_name} "
                "mostrando seus benefícios e vantagens."
            )

        }



    # ===============================
    # CACHE
    # ===============================

    save_cache(
        "scripts",
        product_name,
        script
    )



    print(
        "\n========== SCRIPT GERADO =========="
    )

    print(
        script
    )

    print(
        "===================================\n"
    )



    return script