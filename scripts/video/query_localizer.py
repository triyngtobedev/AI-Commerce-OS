"""
Normaliza queries de busca e T2V para inglês.

Stock APIs (Pexels, Wikimedia) e modelos de vídeo IA respondem melhor a
prompts em inglês. Este módulo traduz termos comuns do português sem chamar IA.
"""

from __future__ import annotations

import re
import unicodedata

# Cenas onde Pollinations degrada demais a percepção de qualidade.
CRITICAL_SCENE_TIPOS = frozenset({"hook", "revelacao", "encerramento"})

# Intents/assets que devem priorizar Wikimedia Commons (arquivo histórico).
WIKIMEDIA_PRIORITY_ASSETS = frozenset({
    "documentary_image",
    "historical_photo",
    "old_map",
    "animated_map",
    "military_documents",
    "archive_video",
    "ww2_archive_video",
    "europe_map",
})

WIKIMEDIA_PRIORITY_INTENTS = frozenset({
    "historical_context",
    "historical_event",
    "investigation",
    "ancient_ruins",
    "old_map",
    "dramatic_reveal",
    "impact_consequences",
})

# Traduções parciais — ordem importa (frases compostas primeiro).
_PT_PHRASES: tuple[tuple[str, str], ...] = (
    ("segunda guerra mundial", "world war ii"),
    ("primeira guerra mundial", "world war i"),
    ("guerra mundial", "world war"),
    ("operação barbarossa", "operation barbarossa"),
    ("exército vermelho", "red army"),
    ("exercito vermelho", "red army"),
    ("força aérea", "air force"),
    ("forca aerea", "air force"),
    ("documentário histórico", "historical documentary"),
    ("documentario historico", "historical documentary"),
    ("arquivo histórico", "historical archive"),
    ("arquivo historico", "historical archive"),
    ("mapa histórico", "historical map"),
    ("mapa historico", "historical map"),
    ("fotografia histórica", "historical photograph"),
    ("fotografia historica", "historical photograph"),
    ("batalha de", "battle of"),
    ("invasão da", "invasion of"),
    ("invasao da", "invasion of"),
    ("tropas alemãs", "german troops"),
    ("tropas alemas", "german troops"),
    ("tropas soviéticas", "soviet troops"),
    ("tropas sovieticas", "soviet troops"),
)

_PT_WORDS: dict[str, str] = {
    "guerra": "war",
    "batalha": "battle",
    "exército": "army",
    "exercito": "army",
    "soldados": "soldiers",
    "tanques": "tanks",
    "aviões": "airplanes",
    "avioes": "airplanes",
    "bombardeio": "bombing",
    "invasão": "invasion",
    "invasao": "invasion",
    "mapa": "map",
    "documento": "document",
    "documentos": "documents",
    "arquivo": "archive",
    "histórico": "historical",
    "historico": "historical",
    "história": "history",
    "historia": "history",
    "mistério": "mystery",
    "misterio": "mystery",
    "explosão": "explosion",
    "explosao": "explosion",
    "desastre": "disaster",
    "civilização": "civilization",
    "civilizacao": "civilization",
    "império": "empire",
    "imperio": "empire",
    "reino": "kingdom",
    "século": "century",
    "seculo": "century",
    "expedição": "expedition",
    "expedicao": "expedition",
    "pesquisa": "research",
    "investigação": "investigation",
    "investigacao": "investigation",
    "consequências": "consequences",
    "consequencias": "consequences",
    "impacto": "impact",
    "revelação": "revelation",
    "revelacao": "revelation",
    "floresta": "forest",
    "montanha": "mountain",
    "oceano": "ocean",
    "cidade": "city",
    "ruínas": "ruins",
    "ruinas": "ruins",
    "antigo": "ancient",
    "antiga": "ancient",
    "medieval": "medieval",
    "nazista": "nazi",
    "nazistas": "nazi",
    "alemão": "german",
    "alemao": "german",
    "alemães": "german",
    "alemaes": "german",
    "francês": "french",
    "frances": "french",
    "inglês": "english",
    "ingles": "english",
    "russo": "russian",
    "rússia": "russia",
    "russia": "russia",
    "europa": "europe",
    "sibéria": "siberia",
    "siberia": "siberia",
    "operacao": "operation",
    "operação": "operation",
}

_EN_DOC_MARKERS = re.compile(
    r"\b("
    r"documentary|historical|archive|footage|aerial|cinematic|"
    r"world war|ww2|wwii|battle|invasion|establishing"
    r")\b",
    re.IGNORECASE,
)

_PT_MARKERS = re.compile(
    r"\b("
    r"guerra|batalha|histórico|historico|história|historia|"
    r"documentário|documentario|mapa|invasão|invasao|"
    r"exército|exercito|mistério|misterio|século|seculo"
    r")\b",
    re.IGNORECASE,
)


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def looks_portuguese(text: str) -> bool:
    """Heurística leve — detecta queries provavelmente em português."""
    if not text or not text.strip():
        return False
    if _EN_DOC_MARKERS.search(text) and not _PT_MARKERS.search(text):
        return False
    if _PT_MARKERS.search(text):
        return True
    # Acentos típicos do português
    return bool(re.search(r"[áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ]", text))


def localize_search_query(text: str, *, append_documentary: bool = True) -> str:
    """
    Converte query para inglês quando parece português.

    Preserva termos próprios e anos. Não chama APIs externas.
    """
    cleaned = " ".join((text or "").split()).strip()
    if not cleaned:
        return cleaned

    if not looks_portuguese(cleaned):
        return cleaned

    lowered = _strip_accents(cleaned).lower()

    for pt_phrase, en_phrase in _PT_PHRASES:
        if pt_phrase in lowered:
            lowered = lowered.replace(pt_phrase, en_phrase)

    tokens = re.findall(r"[a-z0-9]+", lowered)
    translated: list[str] = []
    for token in tokens:
        translated.append(_PT_WORDS.get(token, token))

    result = " ".join(translated).strip()
    if append_documentary and not _EN_DOC_MARKERS.search(result):
        result = f"{result} historical documentary"
    return result[:100].strip()


def wikimedia_query_variants(query: str, query_item: dict | None = None) -> list[str]:
    """Gera variações de busca otimizadas para Wikimedia Commons."""
    base = localize_search_query(query, append_documentary=False)
    variants: list[str] = []

    for candidate in (base, f"{base} photograph", f"{base} archive"):
        cleaned = " ".join(candidate.split()).strip()
        if cleaned and cleaned not in variants:
            variants.append(cleaned)

    if query_item:
        primary = query_item.get("primary_asset") or ""
        direction = query_item.get("visual_direction") or {}
        asset = primary or direction.get("primary_asset", "")
        if asset in {"old_map", "animated_map", "europe_map"} and "map" not in base:
            variants.append(f"{base} map".strip())
        if asset in {"military_documents", "documentary_image"}:
            variants.append(f"{base} document scan".strip())

    return variants[:4]


def should_prioritize_wikimedia(query_item: dict | None) -> bool:
    """True quando a cena deve buscar arquivo histórico antes de stock genérico."""
    if not query_item:
        return False

    if query_item.get("primary_asset") in WIKIMEDIA_PRIORITY_ASSETS:
        return True
    if query_item.get("visual_intent") in WIKIMEDIA_PRIORITY_INTENTS:
        return True

    direction = query_item.get("visual_direction") or {}
    if direction.get("primary_asset") in WIKIMEDIA_PRIORITY_ASSETS:
        return True
    if direction.get("visual_type") in {
        "historical_documentary",
        "geographic_explanation",
        "investigation",
        "dramatic_event",
    }:
        return True

    return False


def is_critical_scene(tipo: str) -> bool:
    """Cenas onde Pollinations e placeholders IA baratos são bloqueados."""
    return (tipo or "").strip().lower() in CRITICAL_SCENE_TIPOS
