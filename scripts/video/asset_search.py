"""
Asset Search

Gera a lista de queries de busca de mídia a partir das cenas.

Cada query possui 3 níveis de fallback:
    busca           — query específica (vinda do visual da cena)
    busca_tematica  — query temática genérica (ex: "forest fire aerial")
    busca_atmosfera — query de emoção/atmosfera (ex: "mysterious dark forest")
    busca_fallback  — fallback legado por ângulo + tipo de cena
"""


from scripts.core.visual_intent_engine import (
    build_visual_search_query,
    resolve_visual_intent,
)
from scripts.core.visual_director_engine import direct_scene_visual
from scripts.video.query_localizer import localize_search_query
from scripts.video.scene_emotion import SCENE_SECTION_ALIASES
from scripts.video.scene_timeline import ensure_scenes_payload
from scripts.video.media_search_orchestrator import generate_scene_queries
from scripts.youtube.lofi_dark_config import is_lofi_dark, lofi_background_query


# Termos de fallback por ângulo — usados quando
# a query principal não retorna resultados no Pexels.
_FALLBACK_BY_ANGLE = {
    "problema_solucao": "problem solution product demonstration",
    "transformacao_ambiente": "home transformation lifestyle",
    "resultado_visual": "impressive product result close up",
    "produto_viral": "trending product unboxing reaction",
    "beneficio_direto": "practical product daily use",
    "misterio_nao_resolvido": "mysterious historical event documentary",
    "revelacao_historica": "historical revelation archive footage",
    "fato_surpreendente": "surprising historical fact documentary",
    "impacto_historico": "historical impact civilization documentary",
    "cronologia_epica": "epic historical timeline cinematic",
}

_FALLBACK_DEFAULT = "historical documentary cinematic footage"

# Nível 2 — queries temáticas genéricas por tipo de cena.
# Queries muito específicas em inglês falham no Pixabay/Pexels;
# estes termos são mais amplos e retornam resultados relevantes.
_THEMATIC_BY_TIPO = {
    "hook": "dramatic opening cinematic landscape",
    "contexto": "historical documentary establishing shot archive",
    "desenvolvimento_1": "historical event investigation documentary",
    "desenvolvimento_2": "scientific expedition research documentary",
    "revelacao": "dramatic reveal cinematic documentary",
    "revelacao_p2": "mysterious phenomenon sky documentary",
    "consequencias": "impact aftermath devastation documentary",
    "impacto": "modern science research documentary",
    "encerramento": "cinematic closing atmospheric landscape",
    "abertura": "rain window night dark aesthetic",
    "reflexao_1": "city lights night timelapse dark",
    "reflexao_2": "dark forest fog ambient",
    "reflexao_3": "coffee shop night aesthetic",
    "conexoes": "anime aesthetic dark room",
    "aprofundamento": "ocean waves night slow",
    "demonstracao": "product demonstration close up",
    "beneficio": "positive result lifestyle",
    "cta": "product showcase cinematic",
}

# Nível 3 — queries de emoção/atmosfera por emotion da cena.
_ATMOSPHERE_BY_EMOTION = {
    "impact": "dramatic explosion smoke clouds aerial",
    "mystery": "mysterious dark forest fog atmosphere",
    "calm": "rain window night dark lofi aesthetic",
    "warning": "storm clouds dramatic sky tension",
    "tension": "dark moody cinematic atmosphere",
    "curiosity": "ancient ruins exploration documentary",
    "revelation": "dramatic light beam cinematic reveal",
    "wonder": "cosmic universe stars night sky",
}

# Mapeamento de termos específicos → queries genéricas (nível 2).
_SPECIFIC_TO_THEMATIC = [
    (("explosion", "siberia", "tunguska"), "forest fire devastation aerial"),
    (("expedition", "1908", "russia", "siberia"), "historical expedition snow wilderness"),
    (("meteorite", "meteor", "asteroid"), "meteor sky atmosphere night"),
    (("taiga", "forest", "trees"), "forest devastation fallen trees aerial"),
    (("scientific", "research", "investigation"), "scientist laboratory documentary"),
    (("cosmic", "universe", "space"), "night sky stars milky way"),
    (("map", "historical"), "old map vintage parchment"),
]

_IMAGE_ONLY_INTENTS = {"old_map", "engraving"}


def _build_fallback(angulo, produto, tipo):
    """
    Constrói query de fallback combinando
    o ângulo estratégico com o tipo de cena.
    """

    base_angle = _FALLBACK_BY_ANGLE.get(
        angulo,
        _FALLBACK_DEFAULT
    )

    # Variações por tipo de cena para diversificar
    # o fallback sem perder o contexto do ângulo.
    tipo_suffix = {
        "hook": "attention grabbing dramatic",
        "demonstracao": "in use close up",
        "beneficio": "positive result happy person",
        "cta": "product showcase",
        "contexto": "historical context establishing shot",
        "desenvolvimento_1": "historical event dramatic footage",
        "desenvolvimento_2": "investigation research documentary",
        "revelacao": "dramatic reveal cinematic",
        "consequencias": "impact consequences documentary",
        "impacto": "modern impact legacy footage",
        "encerramento": "cinematic closing atmospheric",
    }.get(tipo, "")

    parts = [base_angle]

    if tipo_suffix:
        parts.append(tipo_suffix)

    return " ".join(parts)


def _build_thematic_query(visual: str, tipo: str, angulo: str) -> str:
    """
    Nível 2 — query temática genérica.
    Tenta mapear termos específicos do visual para queries mais amplas.
    """

    visual_lower = visual.lower()

    for keywords, thematic in _SPECIFIC_TO_THEMATIC:
        if any(kw in visual_lower for kw in keywords):
            return thematic

    return _THEMATIC_BY_TIPO.get(tipo, _FALLBACK_BY_ANGLE.get(angulo, _FALLBACK_DEFAULT))


def _build_atmosphere_query(emotion: str, tipo: str) -> str:
    """Nível 3 — query de emoção/atmosfera."""

    atmosphere = _ATMOSPHERE_BY_EMOTION.get(emotion, "")
    if atmosphere:
        return atmosphere

    tipo_atmosphere = {
        "contexto": "historical atmosphere vintage documentary",
        "desenvolvimento_1": "investigation moody blue tones",
        "desenvolvimento_2": "research atmosphere documentary",
        "consequencias": "impact devastation moody desaturated",
        "encerramento": "atmospheric closing cinematic soft",
    }
    return tipo_atmosphere.get(tipo, "documentary cinematic atmosphere")


def generate_asset_queries(scenes, platform: str = "", timeline=None):
    """
    Gera queries de mídia para cada cena.
    """

    scenes = ensure_scenes_payload(scenes if isinstance(scenes, dict) else {"cenas": scenes})
    queries = []

    angulo = scenes.get("angulo", "")
    produto = scenes.get("produto", "product")
    prefer_image = platform == "youtube_dark"
    timeline_sections = timeline.sections if timeline else []
    lofi_template = is_lofi_dark(scenes.get("roteiro_template"))

    # Indexa seções por section_key para casar cena↔seção pela narrativa,
    # não pela posição. As cenas (8) e as seções do roteiro (~6) não têm
    # a mesma cardinalidade, então o casamento posicional desalinhava a
    # emoção/intenção a partir da 4ª cena.
    sections_by_key = {
        section.section_key: section
        for section in timeline_sections
        if getattr(section, "section_key", "")
    }

    topic_name = produto if isinstance(produto, str) else str(produto)
    topic_en = localize_search_query(topic_name, append_documentary=False)

    for index, scene in enumerate(scenes.get("cenas", [])):

        tipo = scene.get("tipo", "")
        visual = scene.get("visual", "")

        # Extrai contexto narrativo rico da cena para enriquecer queries visuais
        narr_context = scene.get("narracao", scene.get("texto", ""))[:120]

        if lofi_template:
            visual = lofi_background_query(index)
            scene.setdefault("visual_intent", "lofi_ambient")
            scene.setdefault("emotion", "calm")
            scene.setdefault("camera_motion", "slow_pan")
        else:
            section_key = SCENE_SECTION_ALIASES.get(tipo, tipo)
            section = sections_by_key.get(section_key)
            if section is None and index < len(timeline_sections):
                section = timeline_sections[index]

            if section:
                visual = build_visual_search_query(visual or section.text[:80], section)
                scene.setdefault("visual_intent", section.visual_intent)
                scene.setdefault("emotion", section.emotion)
                scene.setdefault("camera_motion", section.camera_motion)

        visual_intent = scene.get("visual_intent", "general_narrative")
        emotion = scene.get("emotion", "calm")

        spec = resolve_visual_intent({
            "visual_intent": visual_intent,
            "emotion": emotion,
            "camera_motion": scene.get("camera_motion", "slow_push"),
        })

        direction = direct_scene_visual(scene)
        direction_dict = direction.to_dict()
        scene.setdefault("visual_direction", direction_dict)

        # Constrói query contextualizada: SEMPRE prefixa com o nome do tópico
        # para que buscas em Pexels/Wikimedia/Pixabay retornem mídia relevante
        # ao tema, não genérica.
        raw_query = visual or narr_context or topic_name
        localized_visual = localize_search_query(raw_query, append_documentary=False)
        # Prefixa com o tópico em inglês para dar contexto semântico
        contextual_busca = f"{topic_en} {localized_visual}".strip()

        if lofi_template:
            thematic = lofi_background_query((index + 1) % 10)
            atmosphere = lofi_background_query((index + 2) % 10)
            fallback = lofi_background_query((index + 3) % 10)
        else:
            thematic = _build_thematic_query(contextual_busca, tipo, angulo)
            atmosphere = _build_atmosphere_query(emotion, tipo)
            fallback = _build_fallback(angulo, produto, tipo)

        query = {
            "tempo": scene.get("tempo", ""),
            "tipo": tipo,
            "busca": contextual_busca,
            "busca_raw": raw_query,
            "topic": topic_name,
            "busca_tematica": localize_search_query(thematic, append_documentary=False),
            "busca_atmosfera": localize_search_query(atmosphere, append_documentary=False),
            "busca_fallback": localize_search_query(fallback, append_documentary=False),
            "visual_intent": visual_intent,
            "emotion": emotion,
            "visual_goal": spec.visual_goal,
            "camera": spec.camera,
            "style": spec.style,
            "avoid": spec.avoid,
            "visual_direction": direction_dict,
            "primary_asset": direction.primary_asset,
            "animation_strategy": direction.animation_strategy,
            "scene_type": scene.get("scene_type", tipo),
            "must_show": scene.get("must_show", visual),
            "avoid_showing": scene.get("avoid_showing", []),
            "asset_queries": scene.get("asset_queries", []),
            "fallback_visual_plan": scene.get("fallback_visual_plan", ""),
            "on_screen_text": scene.get("on_screen_text", ""),
            "pace": scene.get("pace", "medium"),
            "broll_density": scene.get("broll_density", "medium"),
        }

        if not lofi_template:
            query["scene_queries"] = generate_scene_queries(
                {**scene, **query},
                topic=produto,
                asset_queries=scene.get("asset_queries"),
            )

        # Visual Director sobrescreve preferência de mídia quando disponível.
        if direction.primary_asset == "documentary_image":
            query["preferir_imagem"] = True
        elif direction.primary_asset == "archive_video":
            query["preferir_imagem"] = False
        elif direction.primary_asset == "animated_map":
            query["preferir_imagem"] = True
            if "map" not in visual.lower():
                query["busca"] = f"{visual} historical map".strip()
        elif prefer_image and scene.get("visual_intent") in _IMAGE_ONLY_INTENTS:
            query["preferir_imagem"] = True

        queries.append(query)

    return queries