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
"""


def safe_get(data, *keys, default=None):
    """
    Busca segura em dicionários aninhados.
    """

    current = data

    for key in keys:

        if not isinstance(current, dict):
            return default

        current = current.get(
            key,
            default
        )

    return current



def detect_product_angle(product, analysis, opportunity):
    """
    Define o melhor ângulo de venda.
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
            "facilita"
        ]
    ):

        return "problema_solucao"


    if any(
        word in text
        for word in [
            "luz",
            "led",
            "decoracao",
            "smart",
            "inteligente"
        ]
    ):

        return "transformacao_ambiente"


    if any(
        word in text
        for word in [
            "beleza",
            "pele",
            "estetica",
            "cabelo"
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
    Gera gancho inicial do vídeo.
    """

    hooks = {

        "problema_solucao":
            f"Você ainda sofre com esse problema? Conheça o {product_name}",

        "transformacao_ambiente":
            f"Esse produto muda completamente o ambiente da sua casa",

        "resultado_visual":
            f"O resultado desse produto chama atenção em segundos",

        "produto_viral":
            f"O produto do TikTok Shop que está bombando",

        "beneficio_direto":
            f"Uma solução simples para facilitar seu dia a dia"
    }


    return hooks.get(
        angle,
        hooks["beneficio_direto"]
    )



def define_video_style(angle):
    """
    Define estilo visual.
    """

    styles = {

        "problema_solucao":
            "demonstracao_pratica",

        "transformacao_ambiente":
            "antes_depois",

        "resultado_visual":
            "resultado_imediato",

        "produto_viral":
            "trend_viral",

        "beneficio_direto":
            "apresentacao_produto"
    }


    return styles.get(
        angle,
        "apresentacao_produto"
    )



def define_cta(opportunity):
    """
    Define chamada para ação.
    """

    score = safe_get(
        opportunity,
        "score_venda",
        default=0
    )


    if score >= 80:

        return (
            "Aproveite a oferta e confira "
            "esse produto no TikTok Shop"
        )


    return (
        "Clique e veja todos os detalhes "
        "desse produto"
    )



def generate_creative_strategy(
    product,
    analysis,
    opportunity
):
    """
    Gera estratégia criativa completa.
    """

    product_name = product.get(
        "nome",
        "produto"
    )


    angle = detect_product_angle(
        product,
        analysis,
        opportunity
    )


    strategy = {

        "produto":
            product_name,

        "angulo":
            angle,

        "gancho":
            generate_hook(
                angle,
                product_name
            ),

        "estilo_video":
            define_video_style(
                angle
            ),

        "cta":
            define_cta(
                opportunity
            ),

        "objetivo":
            "gerar desejo de compra",

        "formato":
            "video_vertical_tiktok_shop"
    }


    return strategy