"""
Script Generator para YouTube.

Gera roteiro documentário longo via IA.
"""

from scripts.ai.router import ask_ai
from scripts.core.platform_config import YOUTUBE_DARK
from scripts.youtube.narration_utils import (
    count_words,
    validate_narration,
    stitch_script_to_narration,
    clean_script_phrases,
    detect_banned_phrases,
    MIN_NARRATION_WORDS,
)
from scripts.utils.prompt_loader import load_prompt
from scripts.utils.json_parser import parse_json
from scripts.utils.ai_cache import load_cache, save_cache

CACHE_PREFIX = "youtube"


def generate_youtube_script(
    topic,
    analysis,
    opportunity,
    strategy,
):
    """
    Gera roteiro documentário para vídeo YouTube.
    """

    topic_name = topic["nome"]
    angulo = strategy.get("angulo", "default")

    cache_key = f"{topic_name}--{angulo}"

    print(
        f"📜 Roteiro YouTube: {topic_name}"
    )


    cached = load_cache(
        "scripts",
        cache_key,
        prefix=CACHE_PREFIX,
    )

    if cached:

        print(
            f"♻️ Cache de roteiro: {topic_name}"
        )

        return cached


    prompt = load_prompt(
        "script_generation",
        platform="youtube",
    )


    gancho = strategy.get("gancho", "")
    tom = strategy.get("tom_narracao", YOUTUBE_DARK.narration_style)
    duracao = strategy.get(
        "duracao_alvo",
        f"{YOUTUBE_DARK.target_duration_seconds // 60} minutos",
    )
    angulo_label = strategy.get("angulo", "documentario")

    full_prompt = f"""
TASK: YOUTUBE_SCRIPT_GENERATION

{prompt}

## Parâmetros de produção
- Duração alvo: {duracao} ({YOUTUBE_DARK.target_duration_seconds} segundos)
- Mínimo de palavras: {MIN_NARRATION_WORDS}
- Tom de narração: {tom}
- Ângulo criativo: {angulo_label}

## Gancho obrigatório (use como base do hook)
"{gancho}"

Tema:
{topic}

Análise:
{analysis}

Oportunidade:
{opportunity}

Estratégia completa:
{strategy}
"""


    response = ask_ai(
        full_prompt,
        "script",
    )


    script = parse_json(response)


    if not isinstance(script, dict):

        script = _fallback_script(topic, strategy)

    script = clean_script_phrases(script)

    banned = detect_banned_phrases(script)
    if banned:
        print(f"⚠️ Roteiro contém frases genéricas — reescrevendo: {len(banned)}")
        script = _rewrite_banned_script(
            script, topic, strategy, full_prompt, banned
        )

    narration = stitch_script_to_narration(script)
    word_count = count_words(narration)

    for warning in validate_narration(narration):
        print(f"⚠️ Roteiro: {warning}")

    if count_words(narration) < MIN_NARRATION_WORDS:
        script = _expand_script_if_short(
            script, topic, strategy, full_prompt, narration
        )
        narration = stitch_script_to_narration(script)
        word_count = count_words(narration)

    script["_meta"] = {
        "palavras": word_count,
        "gancho_usado": gancho,
        "tom_narracao": tom,
    }


    save_cache(
        "scripts",
        cache_key,
        script,
        prefix=CACHE_PREFIX,
    )


    return script


def _rewrite_banned_script(script, topic, strategy, original_prompt, banned):
    """Reescreve seções com frases genéricas via IA."""

    rewrite_prompt = f"""
{original_prompt}

O roteiro abaixo contém frases GENÉRICAS PROIBIDAS que prejudicam retenção:
{banned}

REESCREVA o JSON completo eliminando:
- "Imagine uma/que..."
- "Junte-se a nós..."
- "Neste vídeo iremos..."
- CTAs robóticos
- Encerramentos artificiais

Mantenha fatos, datas e tensão narrativa. Hook deve prender em 5 segundos.

Roteiro atual:
{script}
"""

    response = ask_ai(rewrite_prompt, "script")
    rewritten = parse_json(response)

    if isinstance(rewritten, dict):
        return clean_script_phrases(rewritten)

    return script


def _expand_script_if_short(script, topic, strategy, original_prompt, narration):
    """
    Solicita expansão do roteiro quando abaixo do mínimo de palavras.
    """

    current_words = count_words(narration)
    needed = MIN_NARRATION_WORDS - current_words

    print(
        f"📝 Expandindo roteiro (+{needed} palavras necessárias)..."
    )

    expand_prompt = f"""
{original_prompt}

O roteiro abaixo tem apenas {current_words} palavras.
EXPANDA para pelo menos {MIN_NARRATION_WORDS} palavras mantendo o JSON.
Adicione detalhes narrativos, tensão e curiosidade — NÃO resuma.

Roteiro atual:
{script}
"""

    response = ask_ai(expand_prompt, "script")
    expanded = parse_json(response)

    if isinstance(expanded, dict) and count_words(
        stitch_script_to_narration(expanded)
    ) > current_words:
        return expanded

    return script


def _fallback_script(topic, strategy):

    nome = topic.get("nome", "este evento")

    gancho = strategy.get(
        "gancho",
        f"A história de {nome} é mais surpreendente do que você imagina."
    )


    return {
        "hook": gancho,
        "contexto": f"Para entender {nome}, precisamos voltar no tempo.",
        "desenvolvimento": f"Os fatos sobre {nome} revelam uma narrativa fascinante.",
        "revelacao": "Mas o que poucos sabem é o detalhe que muda tudo.",
        "consequencias": "As consequências desse evento reverberam até hoje.",
        "encerramento": "Se gostou, inscreva-se para mais histórias incríveis.",
    }
