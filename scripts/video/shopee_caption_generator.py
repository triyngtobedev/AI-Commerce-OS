import json

from scripts.ai.router import ask_ai
from scripts.utils.ai_cache import load_cache, save_cache
from scripts.utils.json_parser import parse_json
from scripts.utils.prompt_loader import load_prompt


def generate_shopee_caption(product, content):
    """
    Gera título, descrição e hashtags para Shopee Vídeo.

    Utiliza cache para evitar chamadas repetidas à IA.
    Em caso de erro, retorna valores vazios sem interromper o pipeline.
    """

    product_name = product["nome"]

    cache = load_cache("shopee_caption", product_name)

    if cache:

        print(
            f"♻️ Legenda Shopee em cache: {product_name}"
        )

        return cache

    print(
        f"🛍️ Gerando legenda Shopee: {product_name}"
    )

    try:

        prompt = (
            load_prompt("shopee_caption")
            + "\n\n### PRODUTO\n"
            + json.dumps(product, ensure_ascii=False, indent=2)
            + "\n\n### CONTEÚDO\n"
            + json.dumps(content, ensure_ascii=False, indent=2)
        )

        response = ask_ai(prompt, "content")

        result = parse_json(response)

        if not isinstance(result, dict):
            raise ValueError("Resposta da IA não é um JSON válido.")

        result.setdefault("titulo", "")
        result.setdefault("descricao", "")
        result.setdefault("hashtags", [])

        save_cache("shopee_caption", product_name, result)

        return result

    except Exception as error:

        print(
            f"[SHOPEE CAPTION] Erro ao gerar legenda: {error}"
        )

        return {
            "titulo": "",
            "descricao": "",
            "hashtags": []
        }