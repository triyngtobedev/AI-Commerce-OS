"""
Scene Generator

Transforma conteúdo + estratégia criativa em cenas visuais.

Cada cena possui:
    tempo      — intervalo do vídeo
    tipo       — hook / demonstracao / beneficio / cta
    visual     — query pronta para busca de mídia (Pexels ou persona)
    narracao   — texto da narração para aquele trecho

O campo `visual` agora consome as `queries_contexto` da estratégia
em vez de strings genéricas hardcoded — garantindo que a mídia
reflita o ângulo definido pelo Strategy Engine.
"""


def _get_query(queries_contexto, index, fallback):
    """
    Retorna a query pelo índice com fallback seguro.
    Evita IndexError caso queries_contexto tenha menos
    de 4 itens por qualquer motivo.
    """

    if (
        queries_contexto
        and isinstance(queries_contexto, list)
        and index < len(queries_contexto)
    ):
        return queries_contexto[index]

    return fallback


def generate_scenes(
    product,
    content,
    creative_strategy=None
):
    """
    Gera as 4 cenas do vídeo.

    Quando creative_strategy está presente e possui
    queries_contexto, cada cena recebe uma query
    alinhada ao ângulo estratégico.

    Quando creative_strategy está ausente ou incompleto,
    usa fallbacks genéricos — mantendo compatibilidade
    com chamadas antigas.
    """

    nome = product["nome"]

    narracao = content.get("texto_narracao", "")
    descricao = content.get("descricao", narracao)

    # ===============================
    # EXTRAIR DADOS DA ESTRATÉGIA
    # ===============================

    gancho_texto = ""
    cta_texto = ""
    queries_contexto = []
    estilo_video = ""

    if creative_strategy:

        # gancho — sempre string no schema 1.1
        gancho = creative_strategy.get("gancho", "")
        if isinstance(gancho, dict):
            # compatibilidade com versões antigas do engine
            gancho_texto = gancho.get("visual", "")
        else:
            gancho_texto = str(gancho)

        # cta — sempre string no schema 1.1
        cta = creative_strategy.get("cta", "")
        if isinstance(cta, dict):
            cta_texto = cta.get("texto", "")
        else:
            cta_texto = str(cta)

        # queries prontas para mídia — novo no schema 1.1
        queries_contexto = creative_strategy.get(
            "queries_contexto",
            []
        )

        estilo_video = creative_strategy.get(
            "estilo_video",
            ""
        )

    # ===============================
    # FALLBACKS
    # ===============================

    if not gancho_texto:
        gancho_texto = (
            f"person discovering a problem solved by {nome}, "
            "before and after situation"
        )

    if not cta_texto:
        cta_texto = "Clique e garanta o seu."

    # sufixo de estilo para enriquecer queries quando disponível
    sufixo = f", {estilo_video} style" if estilo_video else ""

    # ===============================
    # QUERIES POR CENA
    # ===============================
    #
    # queries_contexto[0] → hook       (impacto inicial)
    # queries_contexto[1] → demonstracao (produto em uso)
    # queries_contexto[2] → beneficio   (resultado)
    # queries_contexto[3] → cta         (produto em destaque)
    #
    # O gancho textual da estratégia é injetado no visual
    # do hook para orientar a persona e o Pexels sobre
    # o tipo de cena esperada, não só o produto.

    visual_hook = _get_query(
        queries_contexto,
        0,
        fallback=gancho_texto
    )

    visual_demo = _get_query(
        queries_contexto,
        1,
        fallback=(
            f"person using {nome} in real life, "
            f"close up demonstration, product in action"
        )
    )

    visual_beneficio = _get_query(
        queries_contexto,
        2,
        fallback=(
            f"clean result after using {nome}, "
            f"happy person showing improvement"
        )
    )

    visual_cta = _get_query(
        queries_contexto,
        3,
        fallback=(
            f"{nome} product showcase, "
            f"modern commercial style, close up"
        )
    )

    # ===============================
    # CENAS
    # ===============================

    scenes = {
        "produto": nome,
        "angulo": creative_strategy.get("angulo", "") if creative_strategy else "",
        "estilo_video": estilo_video,
        "cenas": [
            {
                "tempo": "0-3",
                "tipo": "hook",
                "visual": f"{visual_hook}{sufixo}",
                "narracao": narracao
            },
            {
                "tempo": "3-15",
                "tipo": "demonstracao",
                "visual": f"{visual_demo}{sufixo}",
                "narracao": descricao
            },
            {
                "tempo": "15-25",
                "tipo": "beneficio",
                "visual": f"{visual_beneficio}{sufixo}",
                "narracao": (
                    "Uma solução simples para facilitar o seu dia a dia."
                )
            },
            {
                "tempo": "25-30",
                "tipo": "cta",
                "visual": f"{visual_cta}{sufixo}",
                "narracao": cta_texto
            },
        ]
    }

    # ===============================
    # SEGURANÇA DO PIPELINE
    # ===============================
    
    try:
        return scenes
    except Exception as e:
        print(f"⚠️ Erro inesperado no Scene Generator: {e}")
        # Retorno de segurança para manter o pipeline fluindo
        return {
            "produto": nome,
            "angulo": "fallback",
            "estilo_video": "default",
            "cenas": []
        }