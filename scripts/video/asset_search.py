"""
Asset Search

Gera a lista de queries de busca de mídia a partir das cenas.

Cada query possui 3 níveis de fallback:
    busca           — query específica (vinda do visual da cena)
    busca_tematica  — query temática genérica (ex: "forest fire aerial")
    busca_atmosfera — query de emoção/atmosfera (ex: "mysterious dark forest")
    busca_fallback  — fallback legado por ângulo + tipo de cena
"""


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
    "demonstracao": "product demonstration close up",
    "beneficio": "positive result lifestyle",
    "cta": "product showcase cinematic",
}

# Nível 3 — queries de emoção/atmosfera por emotion da cena.
_ATMOSPHERE_BY_EMOTION = {
    "impact": "dramatic explosion smoke clouds aerial",
    "mystery": "mysterious dark forest fog atmosphere",
    "calm": "peaceful landscape documentary aerial",
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

    Consome:
        scenes["cenas"]       — lista de cenas com campo visual
        scenes["angulo"]      — ângulo estratégico (novo no schema 1.1)
        scenes["estilo_video"] — estilo visual (novo no schema 1.1)
        timeline              — EmotionalTimeline opcional para visual_intent

    Retorna lista de dicts com:
        tempo, tipo, busca, busca_fallback, visual_intent, emotion
        preferir_imagem (youtube_dark + cenas documentais)
    """

    from scripts.core.visual_intent_engine import (
        build_visual_search_query,
        resolve_visual_intent,
    )
    from scripts.core.visual_director_engine import direct_scene_visual
    from scripts.video.query_localizer import localize_search_query
    from scripts.video.scene_emotion import SCENE_SECTION_ALIASES

    queries = []

    angulo = scenes.get("angulo", "")
    produto = scenes.get("produto", "product")
    prefer_image = platform == "youtube_dark"
    timeline_sections = timeline.sections if timeline else []

    # Indexa seções por section_key para casar cena↔seção pela narrativa,
    # não pela posição. As cenas (8) e as seções do roteiro (~6) não têm
    # a mesma cardinalidade, então o casamento posicional desalinhava a
    # emoção/intenção a partir da 4ª cena.
    sections_by_key = {
        section.section_key: section
        for section in timeline_sections
        if getattr(section, "section_key", "")
    }

    for index, scene in enumerate(scenes.get("cenas", [])):

        tipo = scene.get("tipo", "")
        visual = scene.get("visual", "")

        # Casa por section_key (com os mesmos aliases usados no render) e,
        # só se não houver correspondência, recorre ao índice posicional.
        section_key = SCENE_SECTION_ALIASES.get(tipo, tipo)
        section = sections_by_key.get(section_key)
        if section is None and index < len(timeline_sections):
            section = timeline_sections[index]

        if section:
            # Query enriquecida (cinematográfica) só quando há timeline —
            # preserva buscas literais de produto (TikTok) sem timeline.
            visual = build_visual_search_query(visual or section.text[:80], section)
            scene.setdefault("visual_intent", section.visual_intent)
            scene.setdefault("emotion", section.emotion)
            scene.setdefault("camera_motion", section.camera_motion)

        visual_intent = scene.get("visual_intent", "general_narrative")
        emotion = scene.get("emotion", "calm")

        # Spec resolvida a partir dos metadados já existentes na cena.
        # Fornece sinais narrativos (visual_goal, camera, style, avoid) para o
        # ranking story-aware — de forma neutra entre todos os providers.
        spec = resolve_visual_intent({
            "visual_intent": visual_intent,
            "emotion": emotion,
            "camera_motion": scene.get("camera_motion", "slow_push"),
        })

        direction = direct_scene_visual(scene)
        direction_dict = direction.to_dict()
        scene.setdefault("visual_direction", direction_dict)

        localized_visual = localize_search_query(visual or produto)
        thematic = _build_thematic_query(localized_visual, tipo, angulo)
        atmosphere = _build_atmosphere_query(emotion, tipo)
        fallback = _build_fallback(angulo, produto, tipo)

        query = {
            "tempo": scene.get("tempo", ""),
            "tipo": tipo,
            "busca": localized_visual,
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
        }

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