"""
Template de roteiro YouTube Dark — 8 cenas documentárias sem API.

Gera roteiro dramático completo via f-strings, sem chamadas de IA.
Cada cena tem exatamente 150 palavras; visual_query sempre em inglês.
"""

from __future__ import annotations

from scripts.core.director_engine import direct_script
from scripts.core.emotional_timeline import build_emotional_timeline
from scripts.core.platform_config import YOUTUBE_DARK
from scripts.core.visual_intent_engine import apply_visual_intents
from scripts.creative.script_parser import enrich_script_with_emotions, sync_script_from_keyed_sections
from scripts.video.query_localizer import localize_search_query
from scripts.youtube.narration_utils import (
    TEMPLATE_8_SCENE_SECTIONS,
    count_words,
    estimate_duration_seconds,
    stitch_script_to_narration,
)

TARGET_SCENE_WORDS = 150

# Frases de preenchimento dramático (usadas só se o template ficar abaixo de 150 palavras).
_PADDING_PHRASES = (
    "Cada detalhe importa nesta investigação.",
    "Os registros não mentem quando sabemos onde olhar.",
    "Poucos ousam confrontar essa versão oficial.",
    "A evidência acumula silenciosamente ao longo dos anos.",
    "Isso muda completamente o que pensávamos saber.",
    "A pergunta certa vale mais que mil respostas prontas.",
    "O silêncio em torno deste tema nunca foi acidental.",
    "Quem investiga de verdade encontra padrões inquietantes.",
)


def _english_visual_query(template: str, topic: str) -> str:
    """Garante visual_query em inglês para APIs de stock/Wikimedia."""

    topic_en = localize_search_query(topic, append_documentary=False)
    query = template.format(topic=topic_en)
    localized = localize_search_query(query, append_documentary=False)
    stopwords = {"do", "da", "de", "dos", "das", "o", "a", "os", "as"}
    words = [word for word in localized.split() if word.lower() not in stopwords]
    return " ".join(words)[:100].strip()


def _ensure_exact_words(text: str, target: int = TARGET_SCENE_WORDS) -> str:
    """Ajusta narração para exatamente `target` palavras."""

    words = text.split()
    if len(words) == target:
        return text
    if len(words) > target:
        return " ".join(words[:target])

    pad_idx = 0
    while len(words) < target:
        phrase_words = _PADDING_PHRASES[pad_idx % len(_PADDING_PHRASES)].split()
        words.extend(phrase_words)
        pad_idx += 1

    return " ".join(words[:target])


SCENE_DEFINITIONS: list[dict] = [
    {
        "id": "gancho",
        "title": "GANCHO",
        "visual_query": "ancient {topic} aerial view dramatic mystery documentary",
        "narration_template": (
            "Você sabia que tudo o que aprendeu sobre {topic} pode estar errado? "
            "O que vou te contar agora vai mudar tudo que você pensou que sabia sobre "
            "{topic}. Não estou falando de teorias da internet ou boatos sem fundamento. "
            "Estou falando de fatos documentados, silenciados e enterrados de propósito. "
            "Por décadas, a narrativa oficial repetiu a mesma história confortável — "
            "sem arestas, sem perguntas incômodas, sem espaço para dúvida. "
            "Mas por trás dessa fachada existe algo que poucos ousam investigar. "
            "Evidências escondidas. Testemunhos apagados. Documentos que desapareceram "
            "nos momentos mais convenientes para quem controlava a narrativa. "
            "Hoje, vamos rasgar o véu. Vamos seguir os rastros que ninguém quis "
            "que você visse. Prepare-se: os próximos minutos podem destruir para "
            "sempre a versão que te contaram sobre {topic}. "
            "Este não é mais um vídeo comum. É uma investigação profunda, perigosa "
            "e impossível de ignorar. E ela começa agora, com uma pergunta simples: "
            "e se tudo fosse mentira?"
        ),
    },
    {
        "id": "contexto",
        "title": "CONTEXTO",
        "visual_query": "{topic} historical archive documents timeline establishing shot",
        "narration_template": (
            "Para entender {topic}, precisamos voltar ao início — não ao início "
            "romantizado dos livros escolares, mas ao momento exato em que os fatos "
            "começaram a se entrelaçar com poder, medo e silêncio deliberado. "
            "Registros históricos mostram que os primeiros relatos sobre {topic} "
            "surgiram em um contexto de incerteza profunda e informação controlada. "
            "Naquele período, poucos tinham acesso à verdade completa. "
            "Os que tinham, frequentemente, tinham motivos para distorcê-la ou "
            "simplificá-la demais. Cartas, diários e relatórios oficiais descrevem "
            "uma realidade muito diferente da versão que chegou até nós. "
            "Arqueólogos e historiadores independentes passaram anos reconstruindo "
            "essa linha do tempo — peça por peça, documento por documento. "
            "O que emergiu foi um quadro complexo, cheio de contradições e lacunas "
            "suspeitas demais para serem coincidência. Por que certas datas não batem? "
            "Por que testemunhas importantes sumiram dos registros oficiais? "
            "Por que a narrativa dominante surgiu tão rápido, como se alguém "
            "tivesse pressa em fechar o caso para sempre?"
        ),
    },
    {
        "id": "misterio",
        "title": "MISTERIO",
        "visual_query": "{topic} unexplained mystery dark conspiracy investigation footage",
        "narration_template": (
            "Aqui a história de {topic} deixa de ser confortável e entra no território "
            "do inexplicável. Existem elementos neste caso que resistem a qualquer "
            "explicação racional dentro do modelo oficial aceito pela academia. "
            "Artefatos encontrados em locais impossíveis. Relatos de testemunhas "
            "separadas por oceanos e gerações, coincidindo em detalhes minúsculos. "
            "Tecnologias descritas séculos antes de existirem oficialmente. "
            "Não estamos falando de coincidências isoladas — estamos falando de um "
            "padrão. Um padrão tão consistente que ignorá-lo exige mais fé cega "
            "do que questioná-lo com honestidade intelectual. Pesquisadores que "
            "ousaram publicar descobertas sobre {topic} enfrentaram censura, "
            "ridicularização pública e, em casos documentados, o fim abrupto "
            "de carreiras promissoras. Por quê? O que há em {topic} que ameaça "
            "tanto a narrativa estabelecida? Alguns acreditam que a resposta está "
            "enterrada em arquivos classificados. Outros apontam interesses "
            "econômicos e políticos que se beneficiam de manter o mistério vivo, "
            "porém controlado. Cada camada removida revela mais perguntas "
            "do que respostas — e isso, por si só, já é uma pista."
        ),
    },
    {
        "id": "evidencia",
        "title": "EVIDENCIA",
        "visual_query": "{topic} forensic evidence documents investigation close up",
        "narration_template": (
            "Chegou a hora de olhar para os fatos concretos ligados a {topic}. "
            "Não opiniões vagas, não especulações vazias — evidências documentadas. "
            "Em arquivos esquecidos de bibliotecas europeias, pesquisadores "
            "encontraram documentos que contradizem frontalmente a versão oficial. "
            "Fotografias analisadas digitalmente revelaram detalhes invisíveis "
            "a olho nu — marcas, inscrições, anomalias estruturais nunca explicadas "
            "de forma satisfatória por nenhum especialista mainstream. "
            "Análises de carbono, luminescência e estudos geológicos independentes "
            "produziram resultados que nenhum museu quis exibir publicamente. "
            "Testemunhos gravados antes da era da manipulação digital contam versões "
            "de {topic} que simplesmente não existem nos livros didáticos. "
            "Cada evidência, isolada, poderia ser contestada individualmente. "
            "Mas juntas, formam um mosaico difícil de ignorar ou descartar. "
            "O cientista que conduziu uma das análises mais rigorosas disse algo "
            "que nunca saiu na imprensa: os números não mentem, mas alguém "
            "claramente preferiu que permanecessem enterrados para sempre."
        ),
    },
    {
        "id": "teoria",
        "title": "TEORIA",
        "visual_query": "{topic} scientific research theory explanation documentary b-roll",
        "narration_template": (
            "Diante de tantas evidências, investigadores de {topic} desenvolveram "
            "teorias que tentam explicar o que a versão oficial se recusa a encarar. "
            "A teoria mais discutida sugere que o que conhecemos como {topic} "
            "é apenas a superfície de algo muito maior — uma rede de conhecimento, "
            "poder e segredo que se estende por milênios inteiros. "
            "Proponentes apontam conexões entre civilizações distantes que não "
            "deveriam ter se comunicado. Similaridades arquitetônicas impossíveis. "
            "Símbolos repetidos em culturas que nunca se encontraram fisicamente. "
            "A explicação convencional exige coincidências em série estatisticamente "
            "improváveis. A teoria alternativa propõe uma única origem — uma fonte "
            "de conhecimento deliberadamente fragmentada, distribuída e parcialmente "
            "destruída ao longo do tempo. Não se trata de fantasias — trata-se de "
            "reavaliação honesta dos dados disponíveis. Historiadores respeitados, "
            "engenheiros renomados e cientistas com carreiras sólidas endossaram "
            "versões desta teoria. Eles não buscam fama ou sensacionalismo barato. "
            "Buscam a verdade que a versão oficial se recusa a encarar de frente."
        ),
    },
    {
        "id": "contra",
        "title": "CONTRA",
        "visual_query": "{topic} debate skepticism controversy argument documentary",
        "narration_template": (
            "Mas nem tudo é o que parece — e seria desonesto ignorar os céticos. "
            "A comunidade acadêmica mainstream mantém posições firmes contra "
            "as teorias alternativas sobre {topic}. Eles argumentam que anomalias "
            "aparentes têm explicações naturais plausíveis, que coincidências são "
            "estatisticamente esperadas em datasets grandes e que a tentação "
            "do mistério distorce interpretações honestas de forma perigosa. "
            "Alguns dos argumentos são sólidos e merecem ser ouvidos com atenção. "
            "Dataciones contestadas foram refeitas. Documentos considerados "
            "definitivos revelaram-se falsificações modernas. Testemunhos-chave "
            "desmoronaram sob escrutínio forense rigoroso. Isso importa profundamente. "
            "Porque a busca pela verdade sobre {topic} exige rigor, não apenas paixão. "
            "Os céticos nos forçam a ser melhores investigadores. "
            "Mas aqui está o detalhe que poucos conseguem explicar satisfatoriamente: "
            "mesmo descartando cada evidência contestada, ainda sobram perguntas "
            "fundamentais sem resposta. Ainda sobram silêncios oficiais suspeitos. "
            "Ainda sobram documentos inacessíveis ao público e à imprensa."
        ),
    },
    {
        "id": "revelacao",
        "title": "REVELACAO",
        "visual_query": "{topic} dramatic revelation truth discovery cinematic reveal",
        "narration_template": (
            "Depois de examinar contexto, mistério, evidências, teorias e "
            "contra-argumentos, chegamos ao que realmente importa sobre {topic}. "
            "A revelação não é uma única bomba — é a compreensão chocante de que "
            "a história oficial foi construída sobre escolhas deliberadas. "
            "Alguém, em algum momento, decidiu quais perguntas valia a pena fazer "
            "e quais deveriam morrer no silêncio para sempre. "
            "Sobre {topic}, as perguntas proibidas são precisamente as mais "
            "importantes de todas. Quando juntamos documentos, anomalias, "
            "silenciamentos e padrões — o quadro que emerge não é confortável. "
            "É desafiador. É transformador. Significa repensar não apenas "
            "{topic}, mas a forma como recebemos informação sobre o passado. "
            "A verdade completa provavelmente nunca será acessível. "
            "Arquivos ainda estão fechados. Testemunhas já se foram. "
            "Mas o que temos é suficiente para concluir uma coisa inegável: "
            "a versão que te contaram é, no mínimo, incompleta de forma sistemática. "
            "E incompletude sistemática não é acidente — é estratégia deliberada."
        ),
    },
    {
        "id": "chamada",
        "title": "CHAMADA",
        "visual_query": "{topic} cinematic closing subscribe dark documentary ending",
        "narration_template": (
            "Se esse vídeo te surpreendeu, imagina o que vem no próximo. "
            "Se este vídeo sobre {topic} abriu sua mente para possibilidades "
            "que você nunca considerou, então nosso trabalho aqui cumpriu "
            "seu propósito mais profundo. Mas a investigação não termina "
            "quando a tela escurece. Cada tema que exploramos neste canal "
            "é um convite — para questionar, pesquisar e formar conclusões "
            "com base em evidências, não em autoridade cega. "
            "{topic} é apenas um capítulo num livro infinito de mistérios "
            "que a história oficial preferiu deixar de lado. "
            "Deixe seu like — isso ajuda o algoritmo a levar essas histórias "
            "para mais pessoas curiosas como você. Inscreva-se e ative o sininho "
            "para não perder a próxima investigação. Compartilhe com alguém "
            "que também questiona o que aprendeu na escola. "
            "Porque quanto mais olhos observam, mais difícil fica esconder "
            "a verdade. Nos comentários, conta: qual aspecto de {topic} "
            "mais te surpreendeu? Queremos ler cada perspectiva. "
            "Até o próximo mistério — e prepare-se, porque o próximo "
            "vai ser ainda mais intenso do que este."
        ),
    },
]


def generate_script_from_template(topic: str) -> dict:
    """
    Gera roteiro documentário completo de 8 cenas sem chamadas de API.

    Args:
        topic: Nome do tema (injetado nos templates via f-string).

    Returns:
        Dict com seções flat (gancho, contexto, ...) e metadados _scenes.
    """
    topic = (topic or "este mistério").strip()
    scenes: list[dict] = []
    script: dict = {}

    for definition in SCENE_DEFINITIONS:
        scene_id = definition["id"]
        raw_narration = definition["narration_template"].format(topic=topic)
        narration = _ensure_exact_words(raw_narration, TARGET_SCENE_WORDS)
        visual_query = _english_visual_query(definition["visual_query"], topic)

        scene = {
            "id": scene_id,
            "title": definition["title"],
            "narration": narration,
            "duration_seconds": 60,
            "visual_query": visual_query,
            "word_count": count_words(narration),
        }
        scenes.append(scene)
        script[scene_id] = narration

    script["hook"] = script["gancho"]
    script["_scenes"] = scenes
    script["_meta"] = {
        "roteiro_template": "documentario_8cenas",
        "script_source": "TEMPLATE",
        "topic": topic,
        "words_per_scene": TARGET_SCENE_WORDS,
    }

    return script


def finalize_template_script(script: dict, topic: dict, strategy: dict) -> dict:
    """
    Enriquece roteiro template para consumo pelo pipeline (sem IA).
    """
    script = dict(script)
    script = sync_script_from_keyed_sections(script)
    script = enrich_script_with_emotions(script)

    directed_script, director_decision = direct_script(script, strategy)
    timeline = build_emotional_timeline(
        directed_script,
        director_meta=director_decision.to_dict(),
    )
    timeline = apply_visual_intents(timeline)

    narration = stitch_script_to_narration(directed_script)
    word_count = count_words(narration)
    estimated_duration = estimate_duration_seconds(narration)

    meta = dict(directed_script.get("_meta") or {})
    meta.update({
        "palavras": word_count,
        "duracao_estimada_segundos": estimated_duration,
        "gancho_usado": directed_script.get("gancho", "")[:120],
        "tom_narracao": strategy.get("tom_narracao", YOUTUBE_DARK.narration_style),
        "roteiro_template": "documentario_8cenas",
        "script_source": "TEMPLATE",
        "director": director_decision.to_dict(),
        "emotional_timeline": timeline.to_dict(),
        "section_order": TEMPLATE_8_SCENE_SECTIONS,
    })
    directed_script["_meta"] = meta

    return directed_script


def template_visual_queries(script: dict) -> list[str]:
    """Extrai queries visuais das cenas do template (sempre em inglês)."""
    scenes = script.get("_scenes") or []
    return [s.get("visual_query", "") for s in scenes if s.get("visual_query")]
