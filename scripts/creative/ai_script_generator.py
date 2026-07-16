from scripts.ai.router import ask_ai
from scripts.creative.script_parser import enrich_script_with_emotions
from scripts.utils.prompt_loader import load_prompt
from scripts.utils.json_parser import parse_json
from scripts.utils.ai_cache import load_cache, save_cache



def _script_cache_key(product_name, creative_strategy=None):
    if not creative_strategy:
        return product_name

    angle = creative_strategy.get(
        "angulo",
        "default"
    )

    return f"{product_name}--{angle}"


def generate_ai_script(
    product,
    analysis,
    opportunity,
    creative_strategy=None
):
    """
    Gera roteiro de vídeo usando IA com cache.

    Retorna o roteiro que será usado
    pelo gerador de conteúdo.
    """


    product_name = product["nome"]

    cache_key = _script_cache_key(
        product_name,
        creative_strategy
    )



    # ===============================
    # CACHE
    # ===============================

    cached = load_cache(
        "scripts",
        cache_key
    )


    if cached:

        print(
            f"♻️ Roteiro em cache: {product_name}"
        )

        return enrich_script_with_emotions(cached)



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

    if creative_strategy:

        full_prompt += f"""

Estratégia criativa:
{creative_strategy}
"""

    # ===============================
    # IA
    # ===============================

    try:
        response = ask_ai(full_prompt, "script")
    except Exception as e:
        print(f"⚠️ Falha na IA: {e}")
        # Retorna um script de fallback para manter o pipeline rodando
        return {
            "gancho": f"Descubra o {product_name}.",
            "roteiro": f"Apresentação rápida do {product_name}."
        }



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

    script = enrich_script_with_emotions(script)

    save_cache(
        "scripts",
        cache_key,
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