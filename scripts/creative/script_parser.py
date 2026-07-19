"""
Parser robusto de roteiros — aceita formato legado e estrutura emocional.

Formato novo:
    {"sections": [{"text": "...", "emotion": "mystery", "intensity": 0.4}]}

Formato legado YouTube:
    {"hook": "...", "contexto": "...", ...}

Formato legado TikTok:
    {"gancho": "...", "roteiro": "..."}
"""

from __future__ import annotations

from typing import Any

YOUTUBE_SECTION_KEYS = [
    "hook",
    "contexto",
    "desenvolvimento",
    "revelacao",
    "consequencias",
    "encerramento",
]

DARK5_SECTION_KEYS = [
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

LOFI_DARK_SECTION_KEYS = [
    "hook",
    "abertura",
    "reflexao_1",
    "reflexao_2",
    "reflexao_3",
    "conexoes",
    "aprofundamento",
    "encerramento",
]

TIKTOK_SECTION_KEYS = [
    "hook",
    "problema",
    "teste",
    "resultado",
    "cta",
]

LEGACY_TIKTOK_KEYS = ["gancho", "roteiro"]

DEFAULT_EMOTION_BY_SECTION: dict[str, str] = {
    "hook": "impact",
    "contexto": "mystery",
    "desenvolvimento": "calm",
    "desenvolvimento_1": "calm",
    "desenvolvimento_2": "calm",
    "revelacao": "mystery",
    "consequencias": "warning",
    "impacto": "impact",
    "encerramento": "calm",
    "fato_1": "impact",
    "fato_2": "mystery",
    "fato_3": "warning",
    "fato_4": "calm",
    "fato_5": "mystery",
    "abertura": "calm",
    "reflexao_1": "calm",
    "reflexao_2": "calm",
    "reflexao_3": "calm",
    "conexoes": "calm",
    "aprofundamento": "calm",
    "problema": "warning",
    "teste": "calm",
    "resultado": "impact",
    "cta": "impact",
    "gancho": "impact",
    "roteiro": "calm",
}

DEFAULT_INTENSITY_BY_EMOTION: dict[str, float] = {
    "mystery": 0.4,
    "impact": 0.9,
    "calm": 0.3,
    "warning": 0.7,
    "sad": 0.6,
    "neutral": 0.5,
}

DEFAULT_VISUAL_INTENT_BY_SECTION: dict[str, str] = {
    "hook": "dramatic_opening",
    "contexto": "historical_context",
    "desenvolvimento": "investigation",
    "desenvolvimento_1": "investigation",
    "desenvolvimento_2": "historical_event",
    "revelacao": "dramatic_reveal",
    "consequencias": "impact_consequences",
    "impacto": "legacy_impact",
    "encerramento": "atmospheric_closing",
    "fato_1": "dramatic_reveal",
    "fato_2": "investigation",
    "fato_3": "historical_event",
    "fato_4": "investigation",
    "fato_5": "dramatic_opening",
    "abertura": "lofi_ambient",
    "reflexao_1": "lofi_ambient",
    "reflexao_2": "lofi_ambient",
    "reflexao_3": "lofi_ambient",
    "conexoes": "lofi_ambient",
    "aprofundamento": "lofi_ambient",
    "problema": "problem_setup",
    "teste": "product_demo",
    "resultado": "result_showcase",
    "cta": "call_to_action",
    "gancho": "attention_grab",
    "roteiro": "general_narrative",
}

DEFAULT_CAMERA_BY_EMOTION: dict[str, str] = {
    "mystery": "slow_push",
    "impact": "fast_zoom",
    "calm": "slow_pan",
    "warning": "shake_light",
    "sad": "slow_pull",
    "neutral": "static",
}

DEFAULT_CAMERA_BY_SECTION: dict[str, str] = {
    "hook": "fast_zoom",
    "contexto": "slow_pan",
    "revelacao": "slow_push",
    "encerramento": "slow_pull",
}

NARRATIVE_TEXT_KEYS = ("text", "narracao", "narrative", "conteudo", "content", "value")


def extract_section_text(value: Any) -> str:
    """
    Extrai texto narrativo de seção em string ou dict (JSON estruturado do LLM).
    """

    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, dict):
        for key in NARRATIVE_TEXT_KEYS:
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
            if isinstance(candidate, dict):
                nested = extract_section_text(candidate)
                if nested:
                    return nested

        for candidate in value.values():
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()

        return ""

    return str(value).strip()


def _resolve_visual_intent(
    section_key: str,
    emotion: str,
    explicit: str = "",
) -> str:
    if explicit:
        return explicit
    if section_key in DEFAULT_VISUAL_INTENT_BY_SECTION:
        return DEFAULT_VISUAL_INTENT_BY_SECTION[section_key]
    emotion_intents = {
        "mystery": "ancient_ruins",
        "impact": "dramatic_event",
        "calm": "peaceful_landscape",
        "warning": "tension_scene",
        "sad": "melancholy_archive",
    }
    return emotion_intents.get(emotion, "general_narrative")


def _resolve_camera_motion(
    section_key: str,
    emotion: str,
    explicit: str = "",
) -> str:
    if explicit:
        return explicit
    if section_key in DEFAULT_CAMERA_BY_SECTION:
        return DEFAULT_CAMERA_BY_SECTION[section_key]
    return DEFAULT_CAMERA_BY_EMOTION.get(emotion, "slow_push")


def _normalize_section(raw: Any, index: int = 0) -> dict[str, Any]:
    if isinstance(raw, str):
        emotion = "calm"
        section_key = f"section_{index}"
        return {
            "text": raw.strip(),
            "emotion": emotion,
            "intensity": DEFAULT_INTENSITY_BY_EMOTION.get(emotion, 0.5),
            "section_key": section_key,
            "visual_intent": _resolve_visual_intent(section_key, emotion),
            "camera_motion": _resolve_camera_motion(section_key, emotion),
            "pause_before": 0.0,
            "pause_after": 0.0,
        }

    if isinstance(raw, dict):
        text = extract_section_text(raw.get("text") or raw.get("narracao") or raw)
        emotion = raw.get("emotion") or raw.get("tom") or "calm"
        intensity = float(raw.get("intensity", DEFAULT_INTENSITY_BY_EMOTION.get(emotion, 0.5)))
        section_key = raw.get("section_key") or raw.get("key") or f"section_{index}"
        return {
            "text": text,
            "emotion": emotion,
            "intensity": max(0.0, min(1.0, intensity)),
            "section_key": section_key,
            "visual_intent": _resolve_visual_intent(
                section_key,
                emotion,
                raw.get("visual_intent", ""),
            ),
            "camera_motion": _resolve_camera_motion(
                section_key,
                emotion,
                raw.get("camera_motion", ""),
            ),
            "pause_before": float(raw.get("pause_before", 0.0)),
            "pause_after": float(raw.get("pause_after", 0.0)),
        }

    return {
        "text": str(raw).strip(),
        "emotion": "calm",
        "intensity": 0.5,
        "section_key": f"section_{index}",
        "visual_intent": "general_narrative",
        "camera_motion": "slow_push",
        "pause_before": 0.0,
        "pause_after": 0.0,
    }


def _sections_from_keyed_dict(script: dict) -> list[dict[str, Any]]:
    """Converte dict legado {hook: text, ...} em lista de seções."""

    if any(key in script for key in ("fato_1", "fato_5")):
        keys = DARK5_SECTION_KEYS
    elif any(key in script for key in LOFI_DARK_SECTION_KEYS[1:3]):
        keys = LOFI_DARK_SECTION_KEYS
    elif any(key in script for key in YOUTUBE_SECTION_KEYS):
        keys = YOUTUBE_SECTION_KEYS
    elif any(key in script for key in TIKTOK_SECTION_KEYS):
        keys = TIKTOK_SECTION_KEYS
    elif any(key in script for key in LEGACY_TIKTOK_KEYS):
        keys = LEGACY_TIKTOK_KEYS
    else:
        keys = [
            key
            for key in script
            if not key.startswith("_") and isinstance(script[key], (str, dict))
        ]

    sections = []
    for index, key in enumerate(keys):
        raw = script.get(key)
        if raw is None:
            continue

        if isinstance(raw, str):
            text = raw.strip()
        elif isinstance(raw, dict):
            text = extract_section_text(raw)
        else:
            text = extract_section_text(raw)

        if not text:
            continue

        if isinstance(raw, dict) and any(
            field in raw for field in ("emotion", "intensity", "visual_intent", "camera_motion")
        ):
            section = _normalize_section(raw, index)
            section["section_key"] = key
            if section["text"]:
                sections.append(section)
            continue

        emotion = DEFAULT_EMOTION_BY_SECTION.get(key, "calm")
        sections.append({
            "text": text,
            "emotion": emotion,
            "intensity": DEFAULT_INTENSITY_BY_EMOTION.get(emotion, 0.5),
            "section_key": key,
            "visual_intent": _resolve_visual_intent(key, emotion),
            "camera_motion": _resolve_camera_motion(key, emotion),
            "pause_before": 0.0,
            "pause_after": 0.0,
        })

    return sections


def parse_script_sections(script: dict | list | str | None) -> dict[str, Any]:
    """
    Normaliza qualquer formato de roteiro para estrutura padrão com sections[].

    Retorna:
        {
            "sections": [{"text", "emotion", "intensity", "section_key", ...}],
            "format": "emotional" | "legacy_youtube" | "legacy_tiktok" | "plain",
            "full_text": str,
        }
    """

    if not script:
        return {"sections": [], "format": "empty", "full_text": ""}

    if isinstance(script, str):
        section = _normalize_section(script)
        return {
            "sections": [section],
            "format": "plain",
            "full_text": section["text"],
        }

    if isinstance(script, list):
        sections = [
            _normalize_section(item, index)
            for index, item in enumerate(script)
        ]
        sections = [s for s in sections if s["text"]]
        return {
            "sections": sections,
            "format": "emotional",
            "full_text": " ".join(s["text"] for s in sections),
        }

    if not isinstance(script, dict):
        return {"sections": [], "format": "unknown", "full_text": ""}

    if "sections" in script and isinstance(script["sections"], list):
        sections = [
            _normalize_section(item, index)
            for index, item in enumerate(script["sections"])
        ]
        sections = [s for s in sections if s["text"]]
        return {
            "sections": sections,
            "format": "emotional",
            "full_text": " ".join(s["text"] for s in sections),
        }

    sections = _sections_from_keyed_dict(script)
    fmt = "legacy_youtube"
    if any(key in script for key in LEGACY_TIKTOK_KEYS):
        fmt = "legacy_tiktok"

    return {
        "sections": sections,
        "format": fmt,
        "full_text": " ".join(s["text"] for s in sections),
    }


def sync_script_from_keyed_sections(script: dict) -> dict:
    """
    Reconstrói sections[] a partir das chaves narrativas de topo.

    Após expansão por seção, o array sections[] pode ficar desatualizado
    enquanto hook/contexto/desenvolvimento etc. já foram ampliados.
    """

    updated = dict(script)
    keyed_sections = _sections_from_keyed_dict(updated)
    if keyed_sections:
        updated["sections"] = keyed_sections
    return updated


def enrich_script_with_emotions(script: dict) -> dict:
    """
    Enriquece roteiro legado com estrutura emocional sem quebrar compatibilidade.
    Preserva chaves originais e adiciona sections[].
    """

    parsed = parse_script_sections(script)
    enriched = dict(script)
    enriched["sections"] = parsed["sections"]
    enriched["_script_format"] = parsed["format"]
    return enriched
