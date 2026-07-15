"""
Creative Strategy Engine

Responsável por definir a estratégia criativa
antes da geração do roteiro.

Entrada:
    produto
    analise
    oportunidade

Saída:
    estratégia de criação do vídeo

Contrato de saída (schema_version: "1.1"):
    Todos os campos são strings simples.
    Nunca retorna dicts aninhados em campos de primeiro nível.
    queries_contexto é uma lista de strings prontas para busca de mídia.
"""


# ===============================
# ÂNGULOS DISPONÍVEIS
# ===============================
#
# problema_solucao     — produto resolve dor clara e visível
# transformacao_ambiente — produto muda o espaço visualmente
# resultado_visual     — o resultado do produto é a atração
# produto_viral        — produto com alto potencial de engajamento
# beneficio_direto     — benefício prático e objetivo
#

ANGULOS = [
    "problema_solucao",
    "transformacao_ambiente",
    "resultado_visual",
    "produto_viral",
    "beneficio_direto",
]

ESTILOS = [
    "demonstracao_pratica",
    "antes_depois",
    "resultado_imediato",
    "trend_viral",
    "apresentacao_produto",
]


def safe_get(data, *keys, default=None):
    """
    Busca segura em dicionários aninhados.
    """

    current = data

    for key in keys:

        if not isinstance(current, dict):
            return default

        current = current.get(key, default)

    return current


def detect_product_angle(product, analysis, opportunity):
    """
    Define o melhor ângulo de venda baseado
    no nome, descrição e análise do produto.
    """

    text = " ".join(
        [
            str(product.get("nome", "")),
            str(product.get("descricao", "")),
            str(analysis),
        ]
    ).lower()

    if any(
        word in text
        for word in [
            "limpa",
            "aspirador",
            "organiza",
            "remove",
            "facilita",
            "sujeira",
            "bagunça",
        ]
    ):
        return "problema_solucao"

    if any(
        word in text
        for word in [
            "luz",
            "led",
            "decoracao",
            "decoração",
            "smart",
            "inteligente",
            "ambiente",
            "ilumina",
        ]
    ):
        return "transformacao_ambiente"

    if any(
        word in text
        for word in [
            "beleza",
            "pele",
            "estetica",
            "estética",
            "cabelo",
            "resultado",
            "antes e depois",
        ]
    ):
        return "resultado_visual"

    score = safe_get(
        opportunity,
        "score_venda",
        default=0
    )

    if score and score >= 80:
        return "produto_viral"

    return "beneficio_direto"


def generate_hook(angle, product_name):
    """
    Gera o gancho de abertura do vídeo.
    Sempre retorna uma string simples.
    """

    hooks = {
        "problema_solucao": (
            f"Você ainda sofre com esse problema? "
            f"Testei o {product_name} para descobrir se resolve de verdade."
        ),
        "transformacao_ambiente": (
            f"Esse produto muda completamente o ambiente — "
            f"olha o antes e depois com o {product_name}."
        ),
        "resultado_visual": (
            f"O resultado do {product_name} chamou minha atenção "
            f"nos primeiros segundos de uso."
        ),
        "produto_viral": (
            f"Esse produto está bombando e eu precisava testar — "
            f"{product_name} vale a pena?"
        ),
        "beneficio_direto": (
            f"Uma solução simples para facilitar o dia a dia — "
            f"testei o {product_name} na prática."
        ),
    }

    return hooks.get(
        angle,
        hooks["beneficio_direto"]
    )


def define_video_style(angle):
    """
    Define estilo visual do vídeo.
    Sempre retorna uma string simples.
    """

    styles = {
        "problema_solucao": "demonstracao_pratica",
        "transformacao_ambiente": "antes_depois",
        "resultado_visual": "resultado_imediato",
        "produto_viral": "trend_viral",
        "beneficio_direto": "apresentacao_produto",
    }

    return styles.get(
        angle,
        "apresentacao_produto"
    )


def define_cta(opportunity):
    """
    Define chamada para ação.
    Sempre retorna uma string simples.
    """

    score = safe_get(
        opportunity,
        "score_venda",
        default=0
    )

    if score >= 80:
        return (
            "Aproveite a oferta e confira "
            "esse produto no TikTok Shop."
        )

    return (
        "Segue @testandogadgets para mais testes reais."
    )


def build_queries_contexto(angle, product_name, estilo):
    """
    Gera lista de termos de busca prontos para uso
    no Pexels e nos prompts de imagem da persona.

    Cada string é uma query autocontida — pode ser
    usada diretamente em search_media ou como
    contexto adicional no prompt do scene_generator.
    """

    base = product_name.lower()

    queries_by_angle = {

        "problema_solucao": [
            f"{base} solving problem demonstration",
            f"person frustrated before using {base}",
            f"satisfying clean result {base}",
            f"before after comparison {base}",
        ],

        "transformacao_ambiente": [
            f"{base} room transformation",
            f"ambient lighting before after {base}",
            f"home decor upgrade {base}",
            f"aesthetic setup {base}",
        ],

        "resultado_visual": [
            f"{base} result close up",
            f"impressive outcome {base}",
            f"person reacting to {base} result",
            f"visual transformation {base}",
        ],

        "produto_viral": [
            f"viral product {base} tiktok",
            f"trending gadget {base}",
            f"unboxing {base} reaction",
            f"must have product {base}",
        ],

        "beneficio_direto": [
            f"{base} in use daily life",
            f"practical gadget {base}",
            f"person using {base} naturally",
            f"product demonstration {base}",
        ],
    }

    return queries_by_angle.get(
        angle,
        queries_by_angle["beneficio_direto"]
    )


def generate_creative_strategy(
    product,
    analysis,
    opportunity
):
    """
    Gera estratégia criativa completa.

    Contrato de saída estável (schema_version 1.1):
    - Todos os campos de primeiro nível são strings ou listas de strings.
    - Nenhum campo aninhado com dicts.
    - queries_contexto é lista de strings prontas para busca.
    """

    product_name = product.get("nome", "produto")

    angle = detect_product_angle(
        product,
        analysis,
        opportunity
    )

    estilo = define_video_style(angle)

    strategy = {

        "schema_version": "1.1",

        "produto": product_name,

        "angulo": angle,

        "gancho": generate_hook(
            angle,
            product_name
        ),

        "estilo_video": estilo,

        "cta": define_cta(opportunity),

        "objetivo": "gerar desejo de compra",

        "formato": "video_vertical_tiktok_shop",

        # Queries prontas para uso no Pexels e
        # nos prompts de imagem da persona.
        # Garante que a mídia reflita o ângulo
        # da estratégia, não apenas o nome do produto.
        "queries_contexto": build_queries_contexto(
            angle,
            product_name,
            estilo
        ),

    }

    return strategy