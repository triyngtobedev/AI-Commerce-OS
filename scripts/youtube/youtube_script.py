"""
Script Generator para YouTube.

Gera roteiro documentário longo via IA.
"""

import os

from scripts.ai.router import ask_ai
from scripts.core.director_engine import direct_script
from scripts.core.emotional_timeline import build_emotional_timeline
from scripts.core.platform_config import YOUTUBE_DARK
from scripts.core.visual_intent_engine import apply_visual_intents
from scripts.creative.script_parser import enrich_script_with_emotions, extract_section_text, sync_script_from_keyed_sections
from scripts.youtube.narration_utils import (
    count_words,
    validate_narration,
    validate_sentence_length,
    validate_scene_hooks,
    stitch_script_to_narration,
    clean_script_phrases,
    detect_banned_phrases,
    estimate_duration_seconds,
    MIN_NARRATION_WORDS,
    WORDS_PER_MINUTE,
)

WORDS_PER_SECTION_EXPANSION = 200
MAX_NARRATION_CHARS = int(os.getenv("MAX_NARRATION_CHARS", "0"))
NARRATION_CHAR_REWRITE_TARGET = int(os.getenv("NARRATION_CHAR_REWRITE_TARGET", "2400"))

SECTIONS_TO_EXPAND = [
    "desenvolvimento",
    "contexto",
    "revelacao",
    "consequencias",
]

DARK5_SECTIONS_TO_EXPAND = [
    "contexto",
    "fato_5",
    "fato_4",
    "fato_3",
    "fato_2",
    "fato_1",
    "revelacao",
    "encerramento",
]

from scripts.youtube.lofi_dark_config import (
    LOFI_DARK_MIN_NARRATION_WORDS,
    LOFI_DARK_SECTIONS_TO_EXPAND,
    LOFI_DARK_TARGET_DURATION_SECONDS,
    is_lofi_dark,
)
from scripts.utils.json_parser import parse_json, safe_parse_json
from scripts.utils.prompt_loader import load_prompt, load_script_prompt
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
    roteiro_template = strategy.get("roteiro_template", "documentario")

    cache_key = f"{topic_name}--{angulo}--{roteiro_template}"

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

        return enrich_script_with_emotions(cached)


    prompt = load_script_prompt(
        "script_generation",
        platform="youtube",
        template=roteiro_template,
    )


    gancho = strategy.get("gancho", "")
    tom = strategy.get("tom_narracao", YOUTUBE_DARK.narration_style)
    duracao = strategy.get(
        "duracao_alvo",
        f"{YOUTUBE_DARK.target_duration_seconds // 60} minutos",
    )
    angulo_label = strategy.get("angulo", "documentario")

    if roteiro_template == "dark5":
        section_metas = """
## Metas por seção — Template Dark5 (OBRIGATÓRIO)
- hook: 50-80 palavras (promessa de ranking, "Você não vai acreditar no número 1...")
- contexto: 150-200 palavras
- fato_5 a fato_2: 50-70 palavras cada (15-20 segundos de cena, com gancho pro próximo)
- fato_1: 70-90 palavras (revelação com ênfase máxima)
- revelacao: 150-200 palavras
- encerramento: 60-100 palavras
"""
        target_words_meta = "entre 1600 e 1800 palavras no total"
        narration_rules = """
## Regras de narração dark (OBRIGATÓRIO)
- Máximo 12 palavras por frase — quebre frases longas em duas ou três
- Tom grave e pausado — nunca apressado
- Use [PAUSA] antes de revelações importantes
- Termine cada seção (exceto encerramento) com gancho: "E isso não é o pior..."
- Proibido linguagem formal, jargão técnico e frases enciclopédicas
"""
    elif is_lofi_dark(roteiro_template):
        section_metas = """
## Metas por seção — Template Lofi Dark / Filosofatos (OBRIGATÓRIO)
- hook: 80-100 palavras (abertura íntima, sem clickbait)
- abertura: 350-450 palavras
- reflexao_1, reflexao_2, reflexao_3: 400-500 palavras cada
- conexoes: 350-450 palavras
- aprofundamento: 350-450 palavras
- encerramento: 80-120 palavras (sem CTA agressivo)
"""
        target_words_meta = "entre 2500 e 3200 palavras no total"
        narration_rules = """
## Regras de narração lofi dark (OBRIGATÓRIO)
- Máximo 15 palavras por frase
- Tom reflexivo — conversa às 2h da manhã, sem urgência
- Use [PAUSA] e [PAUSA LONGA] para respirações e silêncios (2-3s)
- Sem listas numeradas, sem ganchos de retenção agressivos
- Permita divagações filosóficas e referências a pensadores/filmes/músicas
- Encerramento natural — sem pedir inscrição
"""
    else:
        section_metas = """
## Metas por seção (OBRIGATÓRIO)
- hook: 50-80 palavras
- contexto: 200-250 palavras
- desenvolvimento: 500-700 palavras (mínimo 200-250 por parágrafo narrativo)
- revelacao: 200-250 palavras
- consequencias: 200-250 palavras
- encerramento: 60-100 palavras
"""
        target_words_meta = "entre 1600 e 1800 palavras no total"
        narration_rules = """
## Regras de narração dark (OBRIGATÓRIO)
- Máximo 12 palavras por frase — quebre frases longas em duas ou três
- Tom grave e pausado — nunca apressado
- Use [PAUSA] antes de revelações importantes
- Termine cada seção (exceto encerramento) com gancho: "E isso não é o pior..."
- Proibido linguagem formal, jargão técnico e frases enciclopédicas
"""

    if is_lofi_dark(roteiro_template):
        target_seconds = LOFI_DARK_TARGET_DURATION_SECONDS
        min_words = LOFI_DARK_MIN_NARRATION_WORDS
    else:
        target_seconds = YOUTUBE_DARK.target_duration_seconds
        min_words = MIN_NARRATION_WORDS

    full_prompt = f"""
TASK: YOUTUBE_SCRIPT_GENERATION

{prompt}

## Parâmetros de produção
- Template de roteiro: {roteiro_template}
- Duração alvo: {duracao} ({target_seconds} segundos)
- Mínimo de palavras: {min_words}
- Meta de palavras: {target_words_meta}
- Tom de narração: {tom}
- Ângulo criativo: {angulo_label}

{section_metas}

IMPORTANTE: o roteiro DEVE ter {target_words_meta}.
Seções precisam de conteúdo denso — NÃO resuma.

{narration_rules}

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
        "script_generation",
    )

    script = safe_parse_json(response)

    if not isinstance(script, dict):
        print("⚠️ Resposta de roteiro inválida ou truncada — usando fallback")
        script = _fallback_script(topic, strategy, roteiro_template)

    script = clean_script_phrases(script)

    banned = detect_banned_phrases(script)
    if banned:
        print(f"⚠️ Roteiro contém frases genéricas — reescrevendo: {len(banned)}")
        script = _rewrite_banned_script(
            script, topic, strategy, full_prompt, banned
        )

    narration = stitch_script_to_narration(script)
    word_count = count_words(narration)

    if MAX_NARRATION_CHARS > 0 and len(narration) > MAX_NARRATION_CHARS:
        print(
            f"⚠️ Narração longa ({len(narration)} chars > {MAX_NARRATION_CHARS}) "
            f"— reescrevendo (padrão template n8n / limite TTS)"
        )
        script = _rewrite_narration_length(
            script,
            topic,
            strategy,
            max_chars=MAX_NARRATION_CHARS,
            target_chars=min(NARRATION_CHAR_REWRITE_TARGET, MAX_NARRATION_CHARS),
        )
        narration = stitch_script_to_narration(script)
        word_count = count_words(narration)

    for warning in validate_narration(
        narration,
        min_words=min_words,
        target_seconds=target_seconds,
    ):
        print(f"⚠️ Roteiro: {warning}")

    for warning in validate_sentence_length(script):
        print(f"⚠️ Frase longa: {warning}")

    for warning in validate_scene_hooks(script):
        print(f"⚠️ Gancho: {warning}")

    estimated_duration = estimate_duration_seconds(narration)

    if estimated_duration < target_seconds:
        target_words = int((target_seconds / 60) * WORDS_PER_MINUTE)
        print(
            f"📝 Roteiro curto: {estimated_duration}s "
            f"(alvo: {target_seconds}s) — expandindo..."
        )
        try:
            script = expand_script_in_sections(
                script, topic, strategy, target_words, roteiro_template
            )
            script = sync_script_from_keyed_sections(script)
        except Exception as e:
            print(
                f"⚠️ Expansão falhou ({e}) — continuando com roteiro atual"
            )
        narration = stitch_script_to_narration(script)
        word_count = count_words(narration)
        estimated_duration = estimate_duration_seconds(narration)
    else:
        print(
            f"✅ Roteiro atinge duração alvo: {estimated_duration}s "
            f"(alvo: {target_seconds}s) — sem expansão"
        )

    script = sync_script_from_keyed_sections(script)
    script = enrich_script_with_emotions(script)

    directed_script, director_decision = direct_script(script, strategy)
    timeline = build_emotional_timeline(
        directed_script,
        director_meta=director_decision.to_dict(),
    )
    timeline = apply_visual_intents(timeline)

    directed_script["_meta"] = {
        "palavras": word_count,
        "gancho_usado": gancho,
        "tom_narracao": tom,
        "roteiro_template": roteiro_template,
        "director": director_decision.to_dict(),
        "emotional_timeline": timeline.to_dict(),
    }

    save_cache(
        "scripts",
        cache_key,
        directed_script,
        prefix=CACHE_PREFIX,
    )


    return directed_script


def _rewrite_narration_length(
    script,
    topic,
    strategy,
    *,
    max_chars: int,
    target_chars: int,
):
    """
    Encurta roteiro quando excede limite de caracteres (ElevenLabs / TTS).

    Padrão do template n8n dark: IF chars > 2500 → reescrever entre 2300–2400.
    """

    narration = stitch_script_to_narration(script)
    tom = strategy.get("tom_narracao", YOUTUBE_DARK.narration_style)
    topic_name = topic.get("nome", "")

    rewrite_prompt = f"""
TASK: REWRITE_SCRIPT_LENGTH

Rewrite the script JSON below keeping structure, impact and style, but fit the
full narration text between {max(max_chars - 200, 1800)} and {target_chars} characters.

Rules:
- Do NOT exceed {target_chars} characters in the stitched narration.
- Keep facts, dates and narrative tension.
- Tom: {tom}
- Topic: {topic_name}
- Return valid JSON only (same section keys).

Current narration ({len(narration)} chars):
{narration}

Script JSON:
{script}
"""

    response = ask_ai(rewrite_prompt, "script_rewrite")
    rewritten = safe_parse_json(response)

    if isinstance(rewritten, dict):
        return clean_script_phrases(rewritten)

    return script


def _rewrite_banned_script(script, topic, strategy, _original_prompt, banned):
    """Reescreve seções com frases genéricas via IA."""

    tom = strategy.get("tom_narracao", YOUTUBE_DARK.narration_style)
    topic_name = topic.get("nome", "")

    rewrite_prompt = f"""
TASK: REWRITE_SCRIPT_BANNED_PHRASES

O roteiro abaixo contém frases GENÉRICAS PROIBIDAS que prejudicam retenção:
{banned}

REESCREVA o JSON completo eliminando:
- "Imagine uma/que..."
- "Junte-se a nós..."
- "Neste vídeo iremos..."
- CTAs robóticos
- Encerramentos artificiais

Tom: {tom}
Tema: {topic_name}

Mantenha fatos, datas e tensão narrativa. Hook deve prender em 5 segundos.

Roteiro atual:
{script}
"""

    response = ask_ai(rewrite_prompt, "script_rewrite")
    rewritten = safe_parse_json(response)

    if isinstance(rewritten, dict):
        return clean_script_phrases(rewritten)

    return script


def expand_single_section(
    section_key,
    section_text,
    topic,
    strategy,
    additional_words=WORDS_PER_SECTION_EXPANSION,
):
    """Expande uma única seção do roteiro com prompt curto (menor contexto)."""

    topic_name = topic.get("nome", "")
    tom = strategy.get("tom_narracao", YOUTUBE_DARK.narration_style)

    prompt = f"""
TASK: EXPAND_SCRIPT_SECTION

Expanda APENAS a seção "{section_key}" do roteiro documentário sobre "{topic_name}".
Adicione aproximadamente {additional_words} palavras de conteúdo narrativo.
Tom: {tom}
NÃO resuma — adicione detalhes, tensão e curiosidade.

Retorne SOMENTE JSON válido:
{{"{section_key}": "texto expandido da seção"}}

Texto atual ({section_key}):
{section_text}
"""

    response = ask_ai(prompt, "script_expansion")
    parsed = safe_parse_json(response)

    if isinstance(parsed, dict) and parsed.get(section_key):
        return extract_section_text(parsed[section_key])

    return extract_section_text(section_text)


def expand_script_in_sections(script, topic, strategy, target_words, roteiro_template="documentario"):
    """
    Expande o roteiro seção por seção em vez de uma única chamada grande.
    Cada iteração adiciona ~150-200 palavras a uma seção específica.
    """

    script = dict(script)
    current_words = count_words(stitch_script_to_narration(script))
    needed = target_words - current_words
    sections = (
        LOFI_DARK_SECTIONS_TO_EXPAND
        if is_lofi_dark(roteiro_template)
        else DARK5_SECTIONS_TO_EXPAND
        if roteiro_template == "dark5"
        else SECTIONS_TO_EXPAND
    )

    print(
        f"📝 Expandindo roteiro por seções (+{needed} palavras necessárias)..."
    )

    while count_words(stitch_script_to_narration(script)) < target_words:
        made_progress = False

        for section in sections:
            total = count_words(stitch_script_to_narration(script))
            if total >= target_words:
                break

            words_to_add = min(WORDS_PER_SECTION_EXPANSION, target_words - total)

            print(
                f"📝 Expandindo seção '{section}' (+~{words_to_add} palavras)..."
            )

            old_text = extract_section_text(script.get(section))

            try:
                new_text = expand_single_section(
                    section,
                    old_text,
                    topic,
                    strategy,
                    words_to_add,
                )
            except Exception as e:
                print(f"⚠️ Falha ao expandir '{section}': {e}")
                continue

            new_text = extract_section_text(new_text)
            if count_words(new_text) > count_words(old_text):
                script[section] = new_text
                made_progress = True

        if not made_progress:
            print("⚠️ Expansão por seções estagnou — usando roteiro parcial")
            break

    return script


def _fallback_script(topic, strategy, roteiro_template="documentario"):

    nome = topic.get("nome", "este evento")

    gancho = strategy.get(
        "gancho",
        f"A história de {nome} é mais surpreendente do que você imagina."
    )

    if roteiro_template == "dark5":
        return {
            "hook": gancho or f"Você não vai acreditar no que está no número 1 sobre {nome}.",
            "contexto": f"Para entender esta lista sobre {nome}, precisamos de contexto.",
            "fato_5": f"Número 5: o primeiro fato surpreendente sobre {nome}.",
            "fato_4": f"Número 4: a história fica ainda mais estranha.",
            "fato_3": f"Número 3: um detalhe que poucos conhecem.",
            "fato_2": f"Número 2: quase impossível de acreditar.",
            "fato_1": f"Número 1: o fato mais chocante sobre {nome}.",
            "revelacao": "Mas o verdadeiro impacto só fica claro quando olhamos de perto.",
            "encerramento": "Se essa lista te pegou, inscreva-se no canal.",
        }

    if is_lofi_dark(roteiro_template):
        return {
            "hook": gancho or f"São duas da manhã. E talvez seja nessa hora que {nome} finalmente faz sentido.",
            "abertura": f"Para entender {nome}, precisamos desacelerar e escutar o que o silêncio diz.",
            "reflexao_1": f"A primeira camada de {nome} não aparece nos livros didáticos.",
            "reflexao_2": f"Quando olhamos de lado, {nome} conecta memórias que a gente evita.",
            "reflexao_3": f"Há algo em {nome} que fala sobre quem somos quando ninguém está olhando.",
            "conexoes": "As ideias se entrelaçam como fios de uma conversa que nunca termina de verdade.",
            "aprofundamento": "E talvez o ponto não seja a resposta, mas a coragem de ficar com a pergunta.",
            "encerramento": "Boa noite. Deixe isso tocar enquanto o resto do mundo continua.",
        }

    return {
        "hook": gancho,
        "contexto": f"Para entender {nome}, precisamos voltar no tempo.",
        "desenvolvimento": f"Os fatos sobre {nome} revelam uma narrativa fascinante.",
        "revelacao": "Mas o que poucos sabem é o detalhe que muda tudo.",
        "consequencias": "As consequências desse evento reverberam até hoje.",
        "encerramento": "Se gostou, inscreva-se para mais histórias incríveis.",
    }
