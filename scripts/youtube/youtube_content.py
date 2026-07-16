"""
Content Generator para YouTube.

Gera pacote de metadados: título, descrição, tags, thumbnail.
A narração vem exclusivamente do roteiro (fonte única de verdade).
"""

from scripts.ai.router import ask_ai
from scripts.youtube.narration_utils import (
    stitch_script_to_narration,
    narration_metadata,
    validate_narration,
)
from scripts.utils.prompt_loader import load_prompt
from scripts.utils.json_parser import parse_json
from scripts.utils.ai_cache import load_cache, save_cache

CACHE_PREFIX = "youtube"


def generate_youtube_content(
    topic,
    analysis,
    opportunity,
    script,
    strategy,
):
    """
    Gera metadados otimizados para publicação no YouTube.
    A narração é montada a partir do roteiro — nunca reescrita pela IA.
    """

    topic_name = topic["nome"]

    print(
        f"📝 Conteúdo YouTube: {topic_name}"
    )


    cached = load_cache(
        "content",
        topic_name,
        prefix=CACHE_PREFIX,
    )

    if cached:

        print(
            f"♻️ Cache de conteúdo: {topic_name}"
        )

        cached = _apply_narration_from_script(cached, script, strategy, topic)

        return cached


    prompt = load_prompt(
        "content_generation",
        platform="youtube",
    )

    gancho = strategy.get("gancho", "")

    full_prompt = f"""
TASK: YOUTUBE_CONTENT_GENERATION

{prompt}

## Gancho da estratégia (use no título e thumbnail)
"{gancho}"

Tema:
{topic}

Análise:
{analysis}

Oportunidade:
{opportunity}

Roteiro (referência — NÃO reescreva como narração):
{script}

Estratégia:
{strategy}
"""


    response = ask_ai(
        full_prompt,
        "content",
    )


    content = parse_json(response)


    if not isinstance(content, dict):

        content = {}


    content = _apply_narration_from_script(content, script, strategy, topic)


    save_cache(
        "content",
        topic_name,
        content,
        prefix=CACHE_PREFIX,
    )


    return content



def _apply_narration_from_script(content, script, strategy, topic):
    """
    Monta narração a partir do roteiro e enriquece metadados.
    Ignora texto_narracao gerado pela IA de conteúdo.
    """

    content.pop("texto_narracao", None)

    narration = stitch_script_to_narration(script)
    meta = narration_metadata(narration)

    content["texto_narracao"] = narration
    content["duracao"] = meta["duracao"]
    content["narracao_meta"] = meta

    for warning in validate_narration(narration):
        print(f"⚠️ Narração: {warning}")

    content = _ensure_metadata(content, topic, strategy)

    descricao_curta = content.get("descricao_curta", "")

    if descricao_curta and descricao_curta not in content.get("descricao", ""):
        content["descricao"] = (
            f"{descricao_curta}\n\n"
            f"{content.get('descricao', '')}"
        )

    tags = content.get("tags", [])
    tags_en = content.get("tags_ingles", [])

    if tags_en:
        merged = list(dict.fromkeys(tags + tags_en))
        content["tags"] = merged

    return content



def _ensure_metadata(content, topic, strategy=None):

    gancho = ""

    if strategy:
        gancho = strategy.get("gancho", "")

    content.setdefault(
        "titulo",
        _title_from_gancho(gancho, topic.get("nome", "Documentário Histórico"))
    )

    content.setdefault(
        "descricao",
        f"Descubra a história fascinante de {topic.get('nome', '')}."
    )

    content.setdefault(
        "tags",
        topic.get("keywords", ["história", "documentário"])
    )

    content.setdefault(
        "duracao",
        "8 minutos"
    )

    content.setdefault(
        "thumbnail_texto",
        _thumbnail_from_gancho(gancho, topic.get("nome", ""))
    )

    content.setdefault(
        "categoria_youtube",
        _category_from_angle(
            strategy.get("angulo", "") if strategy else ""
        )
    )

    content.setdefault(
        "capitulos",
        []
    )

    content.setdefault(
        "titulo_alternativos",
        []
    )

    return content



def _title_from_gancho(gancho, fallback):
    """Deriva título do gancho quando IA não gera um forte."""

    if gancho and len(gancho) <= 70:
        return gancho

    return fallback



def _thumbnail_from_gancho(gancho, topic_name):
    """Deriva texto de thumbnail curto do gancho."""

    if not gancho:
        return topic_name[:20].upper()

    words = gancho.split()[:4]
    text = " ".join(words).upper()

    if len(text) > 30:
        return topic_name[:15].upper()

    return text



def _category_from_angle(angulo):
    """Mapeia ângulo criativo para categoria YouTube."""

    science_angles = {
        "misterio_nao_resolvido",
        "fato_surpreendente",
        "revelacao_historica",
    }

    if angulo in science_angles:
        return "Science & Technology"

    return "Education"
