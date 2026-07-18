"""
Scene Generator para YouTube.

Gera 8 cenas documentárias com timings proporcionais
para vídeos de 6-10 minutos.
"""

from scripts.core.platform_config import YOUTUBE_DARK
from scripts.video.scene_timeline import SCENE_WEIGHTS, _split_text_by_weights
from scripts.youtube.narration_utils import DARK5_SCRIPT_SECTIONS


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

DARK5_SCENE_TYPES = list(DARK5_SCRIPT_SECTIONS)

SCENE_TIMINGS = [
    "0-17",
    "17-34",
    "34-51",
    "51-68",
    "68-85",
    "85-102",
    "102-119",
    "119-136",
]


def _scene_types_for_strategy(strategy) -> list[str]:
    if strategy and strategy.get("roteiro_template") == "dark5":
        return DARK5_SCENE_TYPES
    return SCENE_TYPES


def _scene_timings_for_types(scene_types: list[str]) -> list[str]:
    """Gera placeholders de tempo — sync_scenes_to_audio sobrescreve depois."""

    step = max(1, YOUTUBE_DARK.target_duration_seconds // max(len(scene_types), 1))
    timings = []
    start = 0
    for _ in scene_types:
        end = start + step
        timings.append(f"{start}-{end}")
        start = end
    return timings


def _get_query(queries_contexto, index, fallback):
    """Retorna query pelo índice com fallback."""

    if (
        queries_contexto
        and isinstance(queries_contexto, list)
        and index < len(queries_contexto)
    ):

        return queries_contexto[index]

    return fallback



def _split_narration(narracao, scene_types):
    """
    Divide narração proporcionalmente ao peso de cada tipo de cena.
    """

    if not narracao:
        return [""] * len(scene_types)

    weights = [SCENE_WEIGHTS.get(tipo, 10) for tipo in scene_types]
    chunks = _split_text_by_weights(narracao, weights)

    while len(chunks) < len(scene_types):
        chunks.append("")

    return chunks[: len(scene_types)]



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

    scene_types = _scene_types_for_strategy(strategy)
    scene_timings = _scene_timings_for_types(scene_types)

    narration_parts = _split_narration(narracao, scene_types)


    cenas = []

    for i, tipo in enumerate(scene_types):

        fallback = (
            f"{keywords[i % len(keywords)]} "
            "historical documentary footage"
        )

        cenas.append({
            "tempo": scene_timings[i],
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
