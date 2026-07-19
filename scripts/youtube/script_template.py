"""
Template de roteiro YouTube Dark — 8 cenas documentárias sem API.

Gera roteiro dramático completo via f-strings, sem chamadas de IA.
"""

from __future__ import annotations

from scripts.core.director_engine import direct_script
from scripts.core.emotional_timeline import build_emotional_timeline
from scripts.core.platform_config import YOUTUBE_DARK
from scripts.core.visual_intent_engine import apply_visual_intents
from scripts.creative.script_parser import enrich_script_with_emotions, sync_script_from_keyed_sections
from scripts.youtube.narration_utils import (
    TEMPLATE_8_SCENE_SECTIONS,
    count_words,
    estimate_duration_seconds,
    stitch_script_to_narration,
)

SCENE_DEFINITIONS: list[dict] = [
    {
        "id": "gancho",
        "title": "GANCHO",
        "visual_query": "{topic} mystery documentary dark atmosphere",
        "narration_template": (
            "E se eu te dissesse que tudo o que você achava saber sobre {topic} "
            "está errado? Não estou falando de detalhes pequenos ou teorias da internet. "
            "Estou falando da própria fundação da história que te contaram. "
            "Por décadas, manuais escolares, documentários superficiais e especialistas "
            "de televisão repetiram a mesma versão confortável — uma narrativa limpa, "
            "sem arestas, sem perguntas incômodas. Mas por trás dessa fachada existe "
            "algo que poucos ousam investigar. Evidências enterradas. Testemunhos "
            "silenciados. Documentos que desapareceram nos momentos mais convenientes. "
            "Hoje, vamos rasgar o véu. Vamos seguir os rastros que ninguém quis que "
            "você visse. Prepare-se: o que vem a seguir pode mudar para sempre "
            "a forma como você enxerga {topic}. E no final deste vídeo, você vai "
            "entender por que tantas pessoas preferem que essa história nunca seja contada. "
            "Este não é mais um vídeo comum. É uma investigação profunda e perigosa. E ela começa agora."
        ),
    },
    {
        "id": "contexto",
        "title": "CONTEXTO",
        "visual_query": "{topic} historical archive footage timeline",
        "narration_template": (
            "Para entender {topic}, precisamos voltar ao início — não ao início "
            "romantizado, mas ao momento exato em que os fatos começaram a se "
            "entrelaçar com o poder, o medo e o silêncio. Registros históricos "
            "mostram que os primeiros relatos sobre {topic} surgiram em um contexto "
            "de incerteza profunda. Naquele período, poucos tinham acesso à informação "
            "completa. Os que tinham, frequentemente, tinham motivos para distorcê-la. "
            "Cartas, diários e relatórios oficiais da época descrevem uma realidade "
            "muito diferente da versão que chegou até nós. Arqueólogos, historiadores "
            "e investigadores independentes passaram anos reconstruindo essa linha do "
            "tempo — peça por peça, documento por documento. O que emergiu foi um "
            "quadro complexo, cheio de contradições e lacunas suspeitas. Por que "
            "certas datas não batem? Por que testemunhas importantes desapareceram "
            "dos registros oficiais? Por que a narrativa dominante surgiu tão "
            "rapidamente, como se alguém tivesse pressa em fechar o caso? "
            "Essas perguntas não são paranoia. São o ponto de partida de toda "
            "investigação séria sobre {topic}."
        ),
    },
    {
        "id": "misterio",
        "title": "MISTERIO",
        "visual_query": "{topic} unexplained mystery conspiracy dark",
        "narration_template": (
            "Aqui a história de {topic} deixa de ser confortável e entra no território "
            "do inexplicável. Existem elementos neste caso que resistem a qualquer "
            "explicação racional dentro do modelo oficial. Artefatos encontrados em "
            "locais impossíveis. Relatos de testemunhas que coincidem em detalhes "
            "minúsculos, mesmo separadas por oceanos e gerações. Tecnologias descritas "
            "séculos antes de existirem oficialmente. Não estamos falando de coincidências "
            "isoladas — estamos falando de um padrão. Um padrão tão consistente que "
            "ignorá-lo exige mais fé do que questioná-lo. Pesquisadores que ousaram "
            "publicar suas descobertas sobre {topic} enfrentaram censura, ridicularização "
            "e, em alguns casos, o fim abrupto de carreiras promissoras. Por quê? "
            "O que há em {topic} que ameaça tanto a narrativa estabelecida? "
            "Alguns acreditam que a resposta está enterrada em arquivos classificados. "
            "Outros apontam para interesses econômicos e políticos que se beneficiam "
            "de manter o mistério vivo — mas controlado. O que sabemos com certeza "
            "é que cada camada que removemos revela mais perguntas do que respostas."
        ),
    },
    {
        "id": "evidencia",
        "title": "EVIDENCIA",
        "visual_query": "{topic} evidence documents investigation forensic",
        "narration_template": (
            "Chegou a hora de olhar para os fatos. Não opiniões, não especulações "
            "vazias — evidências concretas ligadas a {topic}. Em arquivos esquecidos "
            "de bibliotecas europeias, pesquisadores encontraram documentos que "
            "contradizem frontalmente a versão oficial. Fotografias analisadas "
            "digitalmente revelaram detalhes invisíveis a olho nu — marcas, inscrições, "
            "anomalias estruturais que nunca foram explicadas satisfatoriamente. "
            "Análises de carbono, datación por luminescência e estudos geológicos "
            "independentes produziram resultados que nenhum museu quis exibir "
            "publicamente. Testemunhos gravados antes da era da manipulação digital "
            "contam versões da história de {topic} que simplesmente não existem "
            "nos livros didáticos. Cada evidência, isoladamente, poderia ser "
            "contestada. Mas juntas, formam um mosaico difícil de ignorar. "
            "O cientista que conduziu uma das análises mais rigorosas sobre "
            "material relacionado a {topic} disse algo que nunca saiu na imprensa "
            "mainstream: os números não mentem, mas alguém claramente preferiu "
            "que eles permanecessem enterrados. E isso nos leva à pergunta central."
        ),
    },
    {
        "id": "teoria",
        "title": "TEORIA",
        "visual_query": "{topic} theory explanation science research",
        "narration_template": (
            "Diante de tantas evidências, investigadores de {topic} desenvolveram "
            "teorias que tentam explicar o inexplicável. A teoria mais discutida "
            "sugere que o que conhecemos como {topic} é apenas a superfície de "
            "algo muito maior — uma rede de conhecimento, poder e segredo que se "
            "estende por milênios. Proponentes desta visão apontam para conexões "
            "entre civilizações distantes que não deveriam ter se comunicado. "
            "Similaridades arquitetônicas impossíveis. Símbolos repetidos em "
            "culturas que nunca se encontraram. A explicação convencional exige "
            "coincidências em série. A teoria alternativa propõe uma única origem "
            "— uma fonte de conhecimento que foi deliberadamente fragmentada, "
            "distribuída e, em parte, destruída. Não se trata de aliens ou "
            "fantasias — trata-se de uma reavaliação honesta dos dados disponíveis. "
            "Historiadores respeitados, engenheiros renomados e cientistas com "
            "carreiras sólidas endossaram versões desta teoria sobre {topic}. "
            "Eles não buscam fama ou sensacionalismo. Buscam a verdade que "
            "a versão oficial se recusa a encarar. Mas toda teoria forte "
            "precisa resistir ao contra-ataque."
        ),
    },
    {
        "id": "contra",
        "title": "CONTRA",
        "visual_query": "{topic} debate skepticism controversy argument",
        "narration_template": (
            "Mas nem tudo é o que parece — e seria desonesto ignorar os céticos. "
            "A comunidade acadêmica mainstream mantém posições firmes contra "
            "as teorias alternativas sobre {topic}. Eles argumentam que anomalias "
            "aparentes têm explicações naturais, que coincidências são estatisticamente "
            "esperadas e que a tentação do mistério distorce interpretações honestas. "
            "Alguns dos argumentos são sólidos. Dataciones contestadas foram refeitas. "
            "Documentos considerados definitivos revelaram-se falsificações modernas. "
            "Testemunhos chave desmoronaram sob escrutínio forense. Isso importa. "
            "Porque a busca pela verdade sobre {topic} exige rigor, não apenas "
            "paixão. Os céticos nos forçam a ser melhores investigadores. "
            "Mas aqui está o detalhe que poucos céticos conseguem explicar: "
            "mesmo descartando cada evidência contestada, ainda sobram perguntas "
            "fundamentais sem resposta. Ainda sobram silêncios oficiais suspeitos. "
            "Ainda sobram documentos inacessíveis. O debate sobre {topic} não "
            "termina com o ceticismo — ele apenas revela onde a narrativa oficial "
            "é mais frágil do que admite. E é exatamente nessa fragilidade "
            "que encontramos a revelação."
        ),
    },
    {
        "id": "revelacao",
        "title": "REVELACAO",
        "visual_query": "{topic} revelation truth discovery dramatic",
        "narration_template": (
            "Depois de examinar contexto, mistério, evidências, teorias e "
            "contra-argumentos, chegamos ao que realmente importa sobre {topic}. "
            "A revelação não é uma única bomba — é a compreensão de que a história "
            "oficial foi construída sobre escolhas deliberadas. Alguém, em algum "
            "momento, decidiu quais perguntas valia a pena fazer e quais deveriam "
            "morrer no silêncio. Sobre {topic}, as perguntas proibidas são "
            "as mais importantes. Quando juntamos tudo — os documentos, as "
            "anomalias, os silenciamentos, os padrões — o quadro que emerge "
            "não é confortável. É desafiador. É transformador. Significa "
            "repensar não apenas {topic}, mas a forma como recebemos "
            "informação sobre o passado. A verdade sobre {topic} provavelmente "
            "nunca será completa. Arquivos ainda estão fechados. Testemunhas "
            "já se foram. Mas o que temos é suficiente para concluir "
            "uma coisa: a versão que te contaram é, no mínimo, incompleta. "
            "E incompletude, quando sistemática, não é acidente — é estratégia. "
            "Agora você sabe. A pergunta é: o que fazer com esse conhecimento?"
        ),
    },
    {
        "id": "chamada",
        "title": "CHAMADA",
        "visual_query": "{topic} subscribe call to action dark cinematic",
        "narration_template": (
            "Se este vídeo sobre {topic} abriu sua mente para possibilidades "
            "que você nunca considerou, então nosso trabalho aqui cumpriu "
            "seu propósito. Mas a investigação não termina quando a tela escurece. "
            "Cada tema que exploramos neste canal é um convite — para questionar, "
            "para pesquisar, para formar suas próprias conclusões com base em "
            "evidências, não em autoridade cega. {topic} é apenas um capítulo "
            "num livro infinito de mistérios que a história oficial preferiu "
            "deixar de lado. Se você quer continuar essa jornada conosco, "
            "deixe seu like — isso ajuda o algoritmo a levar essas histórias "
            "para mais pessoas curiosas como você. Inscreva-se no canal e "
            "ative o sininho para não perder a próxima investigação. "
            "Compartilhe este vídeo com alguém que também questiona o que "
            "aprendeu na escola. Porque quanto mais olhos observam, "
            "mais difícil fica esconder a verdade. "
            "E nos comentários, conta: qual aspecto de {topic} mais te "
            "surpreendeu? Qual teoria você acredita? Queremos ler cada "
            "perspectiva. Porque a verdade, afinal, se constrói coletivamente. "
            "Até o próximo mistério."
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
        narration = definition["narration_template"].format(topic=topic)
        visual_query = definition["visual_query"].format(topic=topic)

        scene = {
            "id": scene_id,
            "title": definition["title"],
            "narration": narration,
            "duration_seconds": 60,
            "visual_query": visual_query,
        }
        scenes.append(scene)
        script[scene_id] = narration

    script["hook"] = script["gancho"]
    script["_scenes"] = scenes
    script["_meta"] = {
        "roteiro_template": "documentario_8cenas",
        "script_source": "TEMPLATE",
        "topic": topic,
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
    """Extrai queries visuais das cenas do template."""
    scenes = script.get("_scenes") or []
    return [s.get("visual_query", "") for s in scenes if s.get("visual_query")]
