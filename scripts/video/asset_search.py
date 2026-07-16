"""
Asset Search

Gera a lista de queries de busca de mídia a partir das cenas.

Cada query possui:
    tempo   — intervalo da cena
    tipo    — hook / demonstracao / beneficio / cta
    busca   — query principal (vinda do visual da cena)
    busca_fallback — query mais ampla caso a principal
                     não retorne resultados no Pexels

O campo `busca` agora reflete o ângulo estratégico
porque o scene_generator já injeta queries_contexto
no campo `visual` de cada cena.

O campo `busca_fallback` é construído a partir do
ângulo e produto — garantindo que mesmo o fallback
seja relevante para a estratégia, não genérico.
"""


# Termos de fallback por ângulo — usados quando
# a query principal não retorna resultados no Pexels.
_FALLBACK_BY_ANGLE = {
    "problema_solucao": "problem solution product demonstration",
    "transformacao_ambiente": "home transformation lifestyle",
    "resultado_visual": "impressive product result close up",
    "produto_viral": "trending product unboxing reaction",
    "beneficio_direto": "practical product daily use",
    "misterio_nao_resolvido": "mysterious historical event documentary",
    "revelacao_historica": "historical revelation archive footage",
    "fato_surpreendente": "surprising historical fact documentary",
    "impacto_historico": "historical impact civilization documentary",
    "cronologia_epica": "epic historical timeline cinematic",
}

_FALLBACK_DEFAULT = "historical documentary cinematic footage"


def _build_fallback(angulo, produto, tipo):
    """
    Constrói query de fallback combinando
    o ângulo estratégico com o tipo de cena.
    """

    base_angle = _FALLBACK_BY_ANGLE.get(
        angulo,
        _FALLBACK_DEFAULT
    )

    # Variações por tipo de cena para diversificar
    # o fallback sem perder o contexto do ângulo.
    tipo_suffix = {
        "hook": "attention grabbing dramatic",
        "demonstracao": "in use close up",
        "beneficio": "positive result happy person",
        "cta": "product showcase",
        "contexto": "historical context establishing shot",
        "desenvolvimento_1": "historical event dramatic footage",
        "desenvolvimento_2": "investigation research documentary",
        "revelacao": "dramatic reveal cinematic",
        "consequencias": "impact consequences documentary",
        "impacto": "modern impact legacy footage",
        "encerramento": "cinematic closing atmospheric",
    }.get(tipo, "")

    parts = [base_angle]

    if tipo_suffix:
        parts.append(tipo_suffix)

    return " ".join(parts)


def generate_asset_queries(scenes):
    """
    Gera queries de mídia para cada cena.

    Consome:
        scenes["cenas"]       — lista de cenas com campo visual
        scenes["angulo"]      — ângulo estratégico (novo no schema 1.1)
        scenes["estilo_video"] — estilo visual (novo no schema 1.1)

    Retorna lista de dicts com:
        tempo, tipo, busca, busca_fallback
    """

    queries = []

    angulo = scenes.get("angulo", "")
    produto = scenes.get("produto", "product")

    for scene in scenes.get("cenas", []):

        tipo = scene.get("tipo", "")
        visual = scene.get("visual", "")

        query = {
            "tempo": scene.get("tempo", ""),
            "tipo": tipo,
            "busca": visual,
            "busca_fallback": _build_fallback(
                angulo,
                produto,
                tipo
            ),
        }

        queries.append(query)

    return queries