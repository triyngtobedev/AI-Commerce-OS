from scripts.ai.router import ask_ai
from scripts.utils.prompt_loader import load_prompt
from scripts.utils.json_parser import parse_json
# TEMPORARIAMENTE DESATIVADO PARA O TESTE: 
# from scripts.utils.ai_cache import load_cache, save_cache

def generate_content(
    product,
    analysis,
    opportunity,
    script,
    creative_strategy=None
):
    product_name = product["nome"]

    print(f"📝 Gerando conteúdo: {product_name}")

    # ===============================
    # PROMPT
    # ===============================
    prompt = load_prompt("content_generation")

    # Injetando a estratégia no Prompt
    estrategia_texto = f"Estratégia Criativa a seguir:\n{creative_strategy}" if creative_strategy else "Nenhuma estratégia específica fornecida."

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

{estrategia_texto}
"""

    # ===============================
    # IA
    # ===============================
    response = ask_ai(full_prompt, "content")

    # ===============================
    # PARSE JSON
    # ===============================
    content = parse_json(response)

    if not isinstance(content, dict):
        print("❌ Erro: conteúdo retornado pela IA não é JSON válido.")
        content = {}

    # ===============================
    # GARANTIA DE NARRAÇÃO
    # ===============================
    if "texto_narracao" not in content:
        print("⚠️ IA não retornou texto_narracao. Tentando corrigir...")
        content["texto_narracao"] = (
            content.get("narracao", "")
            or content.get("texto", "")
            or content.get("script", "")
        )

    if not content["texto_narracao"]:
        print("⚠️ Texto de narração vazio.")
        content["texto_narracao"] = (
            f"Conheça o {product_name}. "
            "Uma oportunidade incrível para quem busca praticidade e qualidade."
        )

    print("\n========== CONTENT GERADO ==========")
    print(content)
    print("====================================\n")

    return content