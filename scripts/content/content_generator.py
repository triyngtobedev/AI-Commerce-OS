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
    Gera conteúdo para o vídeo.

    Responsável por criar:
    - texto_narracao
    - títulos
    - descrição
    - informações usadas pelo vídeo

    Possui sistema de cache.
    """


    product_name = product["nome"]



    # ===============================
    # CACHE
    # ===============================

    cached = load_cache(
        "content",
        product_name
    )


    if cached:

        if "texto_narracao" in cached:

            print(
                f"♻️ Conteúdo em cache: {product_name}"
            )

            return cached

        else:

            print(
                "⚠️ Cache encontrado, mas sem texto_narracao. Regenerando..."
            )



    print(
        f"📝 Gerando conteúdo: {product_name}"
    )



    # ===============================
    # PROMPT
    # ===============================

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



    # ===============================
    # IA
    # ===============================

    response = ask_ai(
        full_prompt,
        "content",
    )



    # ===============================
    # PARSE JSON
    # ===============================

    content = parse_json(
        response
    )



    if not isinstance(content, dict):

        print(
            "❌ Erro: conteúdo retornado pela IA não é JSON válido."
        )

        content = {}



    # ===============================
    # GARANTIA DE NARRAÇÃO
    # ===============================

    if "texto_narracao" not in content:


        print(
            "⚠️ IA não retornou texto_narracao. Tentando corrigir..."
        )


        content["texto_narracao"] = (

            content.get(
                "narracao",
                ""
            )

            or

            content.get(
                "texto",
                ""
            )

            or

            content.get(
                "script",
                ""
            )

        )



    if not content["texto_narracao"]:


        print(
            "⚠️ Texto de narração vazio."
        )


        content["texto_narracao"] = (

            f"Conheça o {product_name}. "
            "Uma oportunidade incrível para quem busca praticidade e qualidade."
        )



    # ===============================
    # CACHE
    # ===============================

    save_cache(
        "content",
        product_name,
        content
    )



    print(
        "\n========== CONTENT GERADO =========="
    )

    print(
        content
    )

    print(
        "====================================\n"
    )



    return content