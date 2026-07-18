"""
Configuração central do template lofi_dark (estilo Filosofatos).

Formato focado em áudio com footage genérico de fundo, narração contemplativa
e duração alvo de 15–25 minutos.
"""

from pathlib import Path

# Duração alvo: 20 min (meio do intervalo 15–25)
LOFI_DARK_TARGET_DURATION_SECONDS = 1200
LOFI_DARK_MIN_NARRATION_WORDS = 2500
LOFI_DARK_TARGET_NARRATION_WORDS = 3000
LOFI_DARK_MAX_WORDS_PER_SENTENCE = 15

LOFI_BACKGROUND_QUERIES = [
    "rain window night",
    "city lights night timelapse",
    "dark forest fog",
    "coffee shop night aesthetic",
    "anime aesthetic dark",
    "fireplace dark room",
    "ocean waves night",
    "empty street rain",
    "candle flame dark",
    "stars night sky slow",
]

LOFI_DARK_SCRIPT_SECTIONS = [
    "hook",
    "abertura",
    "reflexao_1",
    "reflexao_2",
    "reflexao_3",
    "conexoes",
    "aprofundamento",
    "encerramento",
]

LOFI_DARK_SCENE_TYPES = list(LOFI_DARK_SCRIPT_SECTIONS)

LOFI_DARK_SECTIONS_TO_EXPAND = [
    "abertura",
    "reflexao_1",
    "reflexao_2",
    "reflexao_3",
    "conexoes",
    "aprofundamento",
]

LOFI_DARK_SECTION_TRANSITIONS = {
    "abertura": None,
    "reflexao_1": None,
    "reflexao_2": None,
    "reflexao_3": None,
    "conexoes": None,
    "aprofundamento": None,
    "encerramento": None,
}

LOFI_TITLE_PATTERNS = [
    "{tema} pra ouvir enquanto faz outra coisa",
    "A verdade sobre {tema} | ouça enquanto trabalha",
    "{tema} | para refletir enquanto faz algo",
]

LOFI_THUMBNAIL_QUERIES = [
    "anime aesthetic dark night",
    "digital art purple night contemplative",
    "lofi girl aesthetic dark room",
]

LOFI_LOCAL_BACKGROUND_DIR = Path(__file__).resolve().parents[2] / "assets" / "lofi_background"

LOFI_SOUNDTRACK_QUERY = "lofi dark chill beats ambient night study"


def is_lofi_dark(template: str | None) -> bool:
    return (template or "").strip().lower() == "lofi_dark"


def lofi_background_query(scene_index: int) -> str:
    queries = LOFI_BACKGROUND_QUERIES
    if not queries:
        return "rain window night dark aesthetic"
    return queries[scene_index % len(queries)]
