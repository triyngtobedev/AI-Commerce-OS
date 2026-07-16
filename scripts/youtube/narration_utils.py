"""
Utilitários de narração para vídeos YouTube.

Fonte única de verdade: o roteiro (script) é montado em texto_narracao.
Metadados de conteúdo não reescrevem a narração.
"""

from scripts.core.platform_config import YOUTUBE_DARK

SCRIPT_SECTIONS = [
    "hook",
    "contexto",
    "desenvolvimento",
    "revelacao",
    "consequencias",
    "encerramento",
]

SECTION_TRANSITIONS = {
    "contexto": "Mas para entender o que aconteceu, precisamos voltar no tempo.",
    "desenvolvimento": "E é aqui que a história começa a ficar fascinante.",
    "revelacao": "Mas o que poucos sabem é o detalhe que muda tudo.",
    "consequencias": "E as consequências disso reverberam até hoje.",
    "encerramento": None,
}

MIN_NARRATION_WORDS = 750
TARGET_NARRATION_WORDS = 1000
WORDS_PER_MINUTE = 150


def stitch_script_to_narration(script: dict) -> str:
    """
    Monta texto_narracao a partir das seções do roteiro.
    Preserva todo o conteúdo — nunca resume.
    """

    parts = []

    for key in SCRIPT_SECTIONS:
        text = (script.get(key) or "").strip()

        if not text:
            continue

        parts.append(text)

    return " ".join(parts)


def count_words(text: str) -> int:
    """Conta palavras em texto de narração."""

    if not text:
        return 0

    return len(text.split())


def estimate_duration_seconds(text: str, wpm: int = WORDS_PER_MINUTE) -> int:
    """Estima duração da narração em segundos."""

    words = count_words(text)

    if words == 0:
        return 0

    return int((words / wpm) * 60)


def format_duration_label(seconds: int) -> str:
    """Formata duração para exibição (ex: '8 minutos')."""

    minutes = max(1, round(seconds / 60))

    return f"{minutes} minutos"


def validate_narration(
    text: str,
    min_words: int = MIN_NARRATION_WORDS,
    target_seconds: int = YOUTUBE_DARK.target_duration_seconds,
) -> list:
    """
    Valida narração contra requisitos de duração.
    Retorna lista de avisos (não bloqueia pipeline).
    """

    warnings = []
    words = count_words(text)
    estimated = estimate_duration_seconds(text)

    if words < min_words:
        target_seconds_est = estimate_duration_seconds(
            " ".join(["palavra"] * min_words)
        )
        warnings.append(
            f"Narração curta: {words} palavras "
            f"(mínimo recomendado: {min_words}, "
            f"~{target_seconds_est}s)"
        )

    target_min_words = int(
        (target_seconds / 60) * WORDS_PER_MINUTE * 0.85
    )

    if words < target_min_words:
        warnings.append(
            f"Duração estimada: {estimated}s "
            f"(alvo: {target_seconds}s / ~{target_min_words} palavras)"
        )

    return warnings


def narration_metadata(text: str) -> dict:
    """Metadados derivados da narração final."""

    seconds = estimate_duration_seconds(text)

    return {
        "palavras": count_words(text),
        "duracao_estimada_segundos": seconds,
        "duracao": format_duration_label(seconds),
    }
