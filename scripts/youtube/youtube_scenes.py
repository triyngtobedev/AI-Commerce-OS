"""
Scene Generator para YouTube.

Gera 8 cenas documentárias com timings proporcionais
para vídeos de 6-10 minutos.
"""

from scripts.core.platform_config import YOUTUBE_DARK
from scripts.video.scene_timeline import SCENE_WEIGHTS, _split_text_by_weights


SCENE_TYPES = [
    "hook",
    "contexto",
    "desenvolvimento_1",
    "desenvolvimento_2",
    "revelacao",
    "consequencias",
    "impacto",
    "encerramento",
]

SCENE_TIMINGS = [
    "0-30",
    "30-90",
    "90-180",
    "180-270",
    "270-360",
    "360-420",
    "420-480",
    "480-510",
]


def _get_query(queries_contexto, index, fallback):
    """Retorna query pelo índice com fallback."""

    if (
        queries_contexto
        and isinstance(queries_contexto, list)
        and index < len(queries_contexto)
    ):

        return queries_contexto[index]

    return fallback



def _split_narration(narracao, parts=8):
    """
    Divide narração proporcionalmente ao peso de cada tipo de cena.
    """

    if not narracao:
        return [""] * parts

    weights = []
    for tipo in SCENE_TYPES:
        weights.append(SCENE_WEIGHTS.get(tipo, 10))

    chunks = _split_text_by_weights(narracao, weights)

    while len(chunks) < parts:
        chunks.append("")

    return chunks[:parts]



def generate_youtube_scenes(
    topic,
    content,
    strategy=None,
):
    """
    Gera cenas documentárias para vídeo YouTube horizontal.
    """

    nome = topic["nome"]

    narracao = content.get(
        "texto_narracao",
        ""
    )

    queries_contexto = []

    angulo = "documentario"

    estilo = "documentario_narrado"


    if strategy:

        queries_contexto = strategy.get(
            "queries_contexto",
            []
        )

        angulo = strategy.get(
            "angulo",
            angulo
        )

        estilo = strategy.get(
            "estilo_video",
            estilo
        )


    keywords = topic.get(
        "keywords",
        ["history"]
    )

    narration_parts = _split_narration(
        narracao,
        YOUTUBE_DARK.scene_count,
    )


    cenas = []

    for i, tipo in enumerate(SCENE_TYPES):

        fallback = (
            f"{keywords[i % len(keywords)]} "
            "historical documentary footage"
        )

        cenas.append({
            "tempo": SCENE_TIMINGS[i],
            "tipo": tipo,
            "visual": _get_query(
                queries_contexto,
                i,
                fallback,
            ),
            "narracao": narration_parts[i],
        })


    return {
        "produto": nome,
        "angulo": angulo,
        "estilo_video": estilo,
        "formato": YOUTUBE_DARK.formato,
        "cenas": cenas,
    }
