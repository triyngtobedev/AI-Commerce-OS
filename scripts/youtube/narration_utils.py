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

DARK5_SCRIPT_SECTIONS = [
    "hook",
    "contexto",
    "fato_5",
    "fato_4",
    "fato_3",
    "fato_2",
    "fato_1",
    "revelacao",
    "encerramento",
]

DARK5_SECTION_TRANSITIONS = {
    "contexto": "Mas a lista começa pelo número 5.",
    "fato_5": "Agora, o número 4.",
    "fato_4": "Mas espere — o número 3 é ainda mais surpreendente.",
    "fato_3": "Seguindo a contagem regressiva, o número 2.",
    "fato_2": "E agora, o momento que você esperou — o número 1.",
    "fato_1": "Mas o verdadeiro impacto só fica claro quando olhamos de perto.",
    "revelacao": None,
    "encerramento": None,
}

SECTION_TRANSITIONS = {
    "contexto": "Mas para entender o que aconteceu, precisamos voltar no tempo.",
    "desenvolvimento": "E é aqui que a história começa a ficar fascinante.",
    "revelacao": "Mas o que poucos sabem é o detalhe que muda tudo.",
    "consequencias": "E as consequências disso reverberam até hoje.",
    "encerramento": None,
}


def _script_sections_for(script: dict) -> list[str]:
    """Retorna ordem de seções conforme o template do roteiro."""

    if any(script.get(key) for key in ("fato_1", "fato_5")):
        return DARK5_SCRIPT_SECTIONS
    return SCRIPT_SECTIONS


def _transitions_for(script: dict) -> dict:
    if any(script.get(key) for key in ("fato_1", "fato_5")):
        return DARK5_SECTION_TRANSITIONS
    return SECTION_TRANSITIONS

BANNED_PHRASES = [
    r"Imagine uma\b",
    r"Imagine que\b",
    r"Junte-se a nós",
    r"Neste vídeo iremos",
    r"grandes perguntas da humanidade",
    r"histórias incríveis sobre",
    r"Descubra a história fascinante",
    r"E assim, o mistério\b",
    r"inscreva-se e ative o sininho para mais",
    r"\boutrossim\b",
    r"\bdestarte\b",
    r"\bem virtude de\b",
    r"\bconsoante\b",
    r"\bnotadamente\b",
]

FORMAL_WORDS = [
    "outrossim", "destarte", "consoante", "notadamente",
    "em virtude de", "hodiernamente", "doravante",
]

SCENE_HOOK_PHRASES = [
    "E isso não é o pior",
    "Mas espere",
    "O que vem a seguir",
    "E aqui a história fica",
    "Mas o próximo",
    "Ainda não acabou",
]

MAX_WORDS_PER_SENTENCE = 12

MIN_NARRATION_WORDS = 1600
TARGET_NARRATION_WORDS = 1700
WORDS_PER_MINUTE = 150


def stitch_script_to_narration(script: dict, use_transitions: bool = False) -> str:
    """
    Monta texto_narracao a partir das seções do roteiro.
    Preserva todo o conteúdo — nunca resume.
    """

    parts = []
    sections = _script_sections_for(script)
    transitions = _transitions_for(script)

    for key in sections:
        text = (script.get(key) or "").strip()

        if not text:
            continue

        if use_transitions and parts:
            transition = transitions.get(key)
            if transition:
                parts.append(transition)

        parts.append(text)

    return " ".join(parts)


def clean_script_phrases(script: dict) -> dict:
    """Remove ou substitui frases genéricas/robóticas do roteiro."""

    import re

    cleaned = {}

    replacements = {
        r"^Imagine uma\b": "Em",
        r"^Imagine que\b": "",
        r"Junte-se a nós na exploração do desconhecido[^.]*\.?": (
            "O próximo episódio já está a caminho."
        ),
        r"inscreva-se e ative o sininho para mais histórias incríveis[^.]*\.?": (
            "Se essa história te pegou, inscreva-se no canal."
        ),
        r"E assim, o mistério[^.]*permanece[^.]*\.?": "",
    }

    for key, text in script.items():
        if key.startswith("_") or not isinstance(text, str):
            cleaned[key] = text
            continue

        result = text
        for pattern, replacement in replacements.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        for banned in BANNED_PHRASES:
            if re.search(banned, result, re.IGNORECASE):
                result = re.sub(banned, "", result, flags=re.IGNORECASE)

        result = re.sub(r"\s+", " ", result).strip()
        cleaned[key] = result

    return cleaned


def detect_banned_phrases(script: dict) -> list[str]:
    """Retorna lista de frases proibidas encontradas no roteiro."""

    import re

    found = []

    for key, text in script.items():
        if not isinstance(text, str):
            continue

        for banned in BANNED_PHRASES:
            if re.search(banned, text, re.IGNORECASE):
                found.append(f"{key}: {banned}")

    return found


def validate_sentence_length(
    script: dict,
    max_words: int = MAX_WORDS_PER_SENTENCE,
) -> list[str]:
    """
    Valida se frases respeitam o limite de palavras (estilo dark YouTube).
    Retorna avisos com seção e frase violadora.
    """

    import re

    warnings = []

    for key, text in script.items():
        if key.startswith("_") or not isinstance(text, str):
            continue

        clean = re.sub(r"\[PAUSA\]", "", text, flags=re.IGNORECASE)
        sentences = re.split(r"(?<=[.!?…])\s+", clean)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            word_count = len(sentence.split())
            if word_count > max_words:
                preview = sentence[:60] + ("..." if len(sentence) > 60 else "")
                warnings.append(
                    f"{key}: frase com {word_count} palavras "
                    f"(máx {max_words}): \"{preview}\""
                )

    return warnings


def validate_scene_hooks(script: dict) -> list[str]:
    """Verifica se seções narrativas terminam com gancho de retenção."""

    warnings = []
    sections = _script_sections_for(script)

    for key in sections:
        if key == "encerramento":
            continue

        text = (script.get(key) or "").strip()
        if not text:
            continue

        lower = text.lower()
        has_hook = any(hook.lower() in lower for hook in SCENE_HOOK_PHRASES)
        if not has_hook:
            warnings.append(
                f"{key}: sem gancho de retenção "
                f"(ex: 'E isso não é o pior...')"
            )

    return warnings


def strip_pause_markers(text: str) -> str:
    """Remove marcadores [PAUSA] para legendas e metadados."""

    import re

    return re.sub(r"\s*\[PAUSA\]\s*", " ", text, flags=re.IGNORECASE).strip()


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

    target_min_words = int(TARGET_NARRATION_WORDS * 0.9)

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
