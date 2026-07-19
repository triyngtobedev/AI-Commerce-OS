"""
Timeline de cenas sincronizada com áudio e Emotional Timeline.
"""

import json
import math
import os
import re
from pathlib import Path
from typing import Any, Optional

DISABLE_SCENE_SPLITTING = os.getenv("DISABLE_SCENE_SPLITTING", "true").lower() == "true"

from scripts.core.emotional_timeline import EmotionalTimeline, build_emotional_timeline
from scripts.video.media_probe import probe_duration
from scripts.video.scene_emotion import (
    MAX_SCENE_DURATION,
    MIN_SCENE_DURATION,
    apply_timeline_to_scenes,
)
from scripts.youtube.narration_utils import estimate_duration_seconds

SCENE_WEIGHTS = {
    "hook": 6,
    "contexto": 12,
    "desenvolvimento_1": 18,
    "desenvolvimento_2": 18,
    "revelacao": 18,
    "consequencias": 12,
    "impacto": 12,
    "encerramento": 6,
    "fato_1": 17,
    "fato_2": 17,
    "fato_3": 17,
    "fato_4": 17,
    "fato_5": 17,
    "abertura": 14,
    "reflexao_1": 14,
    "reflexao_2": 14,
    "reflexao_3": 14,
    "conexoes": 12,
    "aprofundamento": 14,
}

DEFAULT_WEIGHT = 10
TRANSITION_SECONDS = 0.4

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")

# Movimentos de câmera (do vocabulário já suportado pelo scene_renderer)
# usados para alternar o Ken Burns entre subcenas que compartilham a mesma
# imagem — evita a sensação de slide estático em seções longas divididas.
_SPLIT_MOTION_CYCLE = [
    "zoom_in_center",
    "pan_right",
    "zoom_out_center",
    "pan_left",
    "drift_up",
    "parallax_right",
]


def _vary_split_motion(base_motion: str, part_idx: int) -> str:
    """
    Alterna o movimento entre subcenas da mesma imagem.
    A primeira subcena mantém o movimento original da cena; as seguintes
    rotacionam por movimentos distintos para dar dinamismo sem nova mídia.
    """

    if part_idx == 0:
        return base_motion

    alternatives = [m for m in _SPLIT_MOTION_CYCLE if m != base_motion]
    return alternatives[(part_idx - 1) % len(alternatives)]


def _scene_dict_from_string(value: str, *, tipo: str) -> dict:
    """Reconstrói dict de cena a partir de narração/query serializada."""

    text = value.strip()
    return {
        "tipo": tipo,
        "narracao": text,
        "visual": text[:120],
    }


def normalize_scene_list(
    raw_cenas: Any,
    *,
    section_order: list[str] | None = None,
) -> list[dict]:
    """
    Garante lista de dicts de cena.

    Corrige formatos legados/incorretos:
      - dict mapeando seção → texto (iterar keys virava str na footage)
      - lista de strings (json.dumps / default=str em artefatos)
      - aninhamento acidental {"cenas": [...]}
    """
    if raw_cenas is None:
        return []

    if isinstance(raw_cenas, dict):
        inner = raw_cenas.get("cenas")
        if isinstance(inner, list) and all(isinstance(item, dict) for item in inner):
            raw_cenas = inner
        elif inner is not None and "cenas" not in raw_cenas:
            raw_cenas = inner

    if isinstance(raw_cenas, list):
        normalized: list[dict] = []
        order = section_order or []
        for index, item in enumerate(raw_cenas):
            if isinstance(item, dict):
                normalized.append(dict(item))
                continue
            if isinstance(item, str):
                try:
                    parsed = json.loads(item)
                    if isinstance(parsed, dict):
                        normalized.append(parsed)
                        continue
                except json.JSONDecodeError:
                    pass
                tipo = order[index] if index < len(order) else f"section_{index + 1}"
                normalized.append(_scene_dict_from_string(item, tipo=tipo))
        return normalized

    if isinstance(raw_cenas, dict):
        from scripts.youtube.narration_utils import TEMPLATE_8_SCENE_SECTIONS

        order = section_order or TEMPLATE_8_SCENE_SECTIONS
        normalized = []
        seen: set[str] = set()

        for key in order:
            if key not in raw_cenas:
                continue
            value = raw_cenas[key]
            if isinstance(value, dict):
                scene = dict(value)
                scene.setdefault("tipo", key)
            elif isinstance(value, str):
                scene = _scene_dict_from_string(value, tipo=key)
            else:
                continue
            normalized.append(scene)
            seen.add(key)

        if normalized:
            return normalized

        for key, value in raw_cenas.items():
            if key in seen or key.startswith("_"):
                continue
            if isinstance(value, dict):
                scene = dict(value)
                scene.setdefault("tipo", key)
            elif isinstance(value, str):
                scene = _scene_dict_from_string(value, tipo=key)
            else:
                continue
            normalized.append(scene)

        return normalized

    return []


def ensure_scenes_payload(scenes: Any) -> dict:
    """Normaliza payload de cenas do pipeline para {"cenas": [dict, ...]}."""

    if not isinstance(scenes, dict):
        return {"cenas": normalize_scene_list(scenes)}

    result = dict(scenes)
    section_order = None
    if result.get("roteiro_template") == "documentario_8cenas":
        from scripts.youtube.narration_utils import TEMPLATE_8_SCENE_SECTIONS

        section_order = list(TEMPLATE_8_SCENE_SECTIONS)

    result["cenas"] = normalize_scene_list(
        result.get("cenas"),
        section_order=section_order,
    )
    return result


def extract_scenes(cenas_data) -> list:
    """Normaliza estrutura de cenas do pipeline."""

    if isinstance(cenas_data, dict):
        if "cenas" in cenas_data and any(
            key in cenas_data for key in ("produto", "angulo", "roteiro_template", "synced")
        ):
            return ensure_scenes_payload(cenas_data)["cenas"]
        return normalize_scene_list(cenas_data)

    if isinstance(cenas_data, list):
        return normalize_scene_list(cenas_data)

    return []


def _scene_weight(scene: dict) -> int:
    tipo = scene.get("tipo", "")
    return SCENE_WEIGHTS.get(tipo, DEFAULT_WEIGHT)


def _split_text_by_weights(text: str, weights: list) -> list:
    """Divide texto proporcionalmente aos pesos das cenas."""

    words = text.split()

    if not words:
        return [""] * len(weights)

    total_weight = sum(weights) or 1
    chunks = []
    start = 0

    for i, weight in enumerate(weights):
        if i == len(weights) - 1:
            chunks.append(" ".join(words[start:]))
            break

        count = max(1, round(len(words) * weight / total_weight))
        end = min(start + count, len(words))
        chunks.append(" ".join(words[start:end]))
        start = end

    return chunks


def _scene_narration_text(scene: dict, fallback: str) -> str:
    """Retorna texto de narração da cena, com fallback global."""

    text = scene.get("narracao", "").strip()
    return text or fallback


def _estimate_scene_durations(scenes: list, narracao: str, audio_duration: float) -> list[float]:
    """Estima duração por cena usando narração local e escala para o áudio real."""

    texts = [_scene_narration_text(scene, "") for scene in scenes]
    if not any(texts):
        weights = [_scene_weight(scene) for scene in scenes]
        texts = _split_text_by_weights(narracao, weights)

    estimates = [
        float(estimate_duration_seconds(text)) if text else _scene_weight(scenes[i])
        for i, text in enumerate(texts)
    ]
    total_estimate = sum(estimates) or 1.0

    durations = []
    for estimate in estimates:
        raw = (estimate / total_estimate) * audio_duration
        durations.append(max(MIN_SCENE_DURATION, round(raw, 2)))

    if durations:
        delta = round(audio_duration - sum(durations), 2)
        durations[-1] = max(MIN_SCENE_DURATION, round(durations[-1] + delta, 2))

    return durations


def _split_narration_at_sentences(text: str, parts: int) -> list[str]:
    """Divide narração em N partes coerentes, preferindo limites de frase."""

    if DISABLE_SCENE_SPLITTING:
        text = text.strip()
        return [text] if text else [""]

    text = text.strip()
    if not text or parts <= 1:
        return [text] if text else [""]

    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    if not sentences:
        return _split_text_by_weights(text, [1] * parts)

    if len(sentences) >= parts:
        chunks = []
        per_part = len(sentences) // parts
        remainder = len(sentences) % parts
        cursor = 0
        for i in range(parts):
            count = per_part + (1 if i < remainder else 0)
            group = sentences[cursor : cursor + count]
            chunks.append(" ".join(group) if group else "")
            cursor += count
        return [c for c in chunks if c.strip()] or [text]

    return _split_text_by_weights(text, [1] * parts)


def _compute_split_count(
    duration: float,
    max_duration: float = MAX_SCENE_DURATION,
    min_duration: float = MIN_SCENE_DURATION,
) -> int:
    """Calcula quantas sub-cenas manter cada bloco entre min e max segundos."""

    if DISABLE_SCENE_SPLITTING:
        return 1

    if duration <= max_duration:
        return 1

    min_parts = max(2, math.ceil(duration / max_duration))
    max_parts = max(1, math.floor(duration / min_duration))
    if max_parts >= min_parts:
        return min_parts
    return min_parts


def _split_durations_evenly(
    duration: float,
    parts: int,
    max_duration: float = MAX_SCENE_DURATION,
    min_duration: float = MIN_SCENE_DURATION,
) -> list[float]:
    """Distribui duração total em partes equilibradas dentro do range 15–20s."""

    if DISABLE_SCENE_SPLITTING:
        return [round(duration, 2)]

    if parts <= 1:
        return [round(duration, 2)]

    target = min(max_duration, max(min_duration, round(duration / parts, 2)))
    durations: list[float] = []
    remaining = duration

    for idx in range(parts):
        if idx == parts - 1:
            part = round(remaining, 2)
        else:
            part = min(target, max_duration, round(remaining - min_duration * (parts - idx - 1), 2))
            part = max(min_duration, min(part, max_duration))
        durations.append(part)
        remaining = round(remaining - part, 2)

    return durations


TEMPLATE_8_SCENE_TEMPLATE = "documentario_8cenas"


def _should_split_scenes(scenes_data: dict) -> bool:
    """Templates documentários não devem ser divididos em sub-cenas."""
    if DISABLE_SCENE_SPLITTING:
        return False
    template = str(scenes_data.get("roteiro_template") or "").lower()
    if "documentario" in template:
        return False
    return True


def split_long_scenes(
    scenes_data: dict,
    max_duration: float = MAX_SCENE_DURATION,
    min_duration: float = MIN_SCENE_DURATION,
) -> dict:
    """
    Divide cenas acima do limite de ritmo em sub-cenas narrativas.
    Preserva metadados emocionais/visuais e referência de mídia original.
    """

    result = ensure_scenes_payload(scenes_data) if isinstance(scenes_data, dict) else {
        "cenas": normalize_scene_list(scenes_data),
    }
    if DISABLE_SCENE_SPLITTING or not _should_split_scenes(result):
        return result
    scenes = list(result.get("cenas", []))
    if not scenes:
        return result

    original_count = result.get("media_scene_count") or len(scenes)
    expanded = []
    current_time = 0.0

    for index, scene in enumerate(scenes):
        duration = float(scene.get("duration_seconds") or 0)
        narration = _scene_narration_text(scene, "")

        if duration <= max_duration or not narration:
            new_scene = dict(scene)
            if duration <= 0:
                duration = float(
                    new_scene.get("duration_hint")
                    or new_scene.get("timeline", {}).get("real_duration")
                    or min_duration
                )
            new_scene["duration_seconds"] = duration
            new_scene["duration_hint"] = duration
            new_scene["media_index"] = scene.get("media_index", index)
            new_scene["tempo_inicio"] = round(current_time, 2)
            new_scene["tempo_fim"] = round(current_time + duration, 2)
            new_scene["tempo"] = f"{int(current_time)}-{int(current_time + duration)}"
            current_time = new_scene["tempo_fim"]
            expanded.append(new_scene)
            continue

        parts = _compute_split_count(duration, max_duration, min_duration)
        text_parts = _split_narration_at_sentences(narration, parts)
        while len(text_parts) < parts:
            text_parts.append("")
        text_parts = text_parts[:parts]

        part_durations = _split_durations_evenly(duration, parts, max_duration, min_duration)

        for part_idx, (text_part, part_duration) in enumerate(zip(text_parts, part_durations)):
            part_duration = max(0.5, part_duration)

            new_scene = dict(scene)
            new_scene["narracao"] = text_part
            new_scene["duration_seconds"] = part_duration
            new_scene["duration_hint"] = part_duration
            new_scene["media_index"] = scene.get("media_index", index)
            new_scene["split_part"] = part_idx + 1
            new_scene["split_total"] = parts

            # A mesma imagem é reutilizada nas subcenas; variar o movimento
            # evita que ela pareça um slide parado por dezenas de segundos.
            base_motion = scene.get("scene_motion") or scene.get("camera_motion", "")
            if base_motion:
                new_scene["scene_motion"] = _vary_split_motion(base_motion, part_idx)
            if parts > 1:
                base_tipo = scene.get("tipo", "")
                new_scene["tipo"] = f"{base_tipo}_p{part_idx + 1}" if part_idx else base_tipo

            new_scene["tempo_inicio"] = round(current_time, 2)
            new_scene["tempo_fim"] = round(current_time + part_duration, 2)
            new_scene["tempo"] = (
                f"{int(new_scene['tempo_inicio'])}-{int(new_scene['tempo_fim'])}"
            )
            current_time = new_scene["tempo_fim"]
            expanded.append(new_scene)

    audio_duration = float(result.get("audio_duration") or 0)
    if audio_duration > 0 and expanded:
        delta = round(audio_duration - current_time, 2)
        if abs(delta) >= 0.01:
            last = expanded[-1]
            last["duration_seconds"] = max(0.5, round(last["duration_seconds"] + delta, 2))
            last["duration_hint"] = last["duration_seconds"]
            last["tempo_fim"] = round(last["tempo_inicio"] + last["duration_seconds"], 2)
            last["tempo"] = f"{int(last['tempo_inicio'])}-{int(last['tempo_fim'])}"

    result["cenas"] = expanded
    result["media_scene_count"] = original_count
    result["scene_split"] = len(expanded) != len(scenes)
    return result


def sync_scenes_to_audio(
    cenas_data,
    narracao: str,
    audio_path: str,
    emotional_timeline: Optional[EmotionalTimeline | dict] = None,
    script: Optional[dict] = None,
) -> dict:
    """
    Sincroniza timings das cenas com duração real do áudio.
    Enriquece cenas com Emotional Timeline quando disponível.
    """

    if isinstance(cenas_data, dict):
        result = ensure_scenes_payload(cenas_data)
        scenes = list(result.get("cenas", []))
    else:
        result = {"cenas": normalize_scene_list(cenas_data)}
        scenes = list(result.get("cenas", []))

    audio_duration = probe_duration(audio_path)

    if audio_duration <= 0 and narracao:
        audio_duration = float(estimate_duration_seconds(narracao))

    if not scenes or audio_duration <= 0:
        return cenas_data if isinstance(cenas_data, dict) else {"cenas": scenes}

    timeline = _resolve_timeline(emotional_timeline, script, audio_duration)

    if timeline and timeline.director_meta.get("synced_to_audio"):
        weights = [_scene_weight(s) for s in scenes]
        narration_parts = [
            _scene_narration_text(scene, "")
            for scene in scenes
        ]
        if not any(narration_parts):
            narration_parts = _split_text_by_weights(narracao, weights)

        base_scenes = []
        for i, scene in enumerate(scenes):
            new_scene = dict(scene)
            new_scene["narracao"] = narration_parts[i]
            base_scenes.append(new_scene)

        result["cenas"] = base_scenes
        result = apply_timeline_to_scenes(result, timeline)
        if _should_split_scenes(result):
            result = split_long_scenes(result)
        return ensure_scenes_payload(result)

    weights = [_scene_weight(s) for s in scenes]
    durations = _estimate_scene_durations(scenes, narracao, audio_duration)
    narration_parts = [
        _scene_narration_text(scene, "")
        for scene in scenes
    ]
    if not any(narration_parts):
        narration_parts = _split_text_by_weights(narracao, weights)

    current = 0.0
    updated = []

    for i, scene in enumerate(scenes):
        duration = durations[i] if i < len(durations) else max(MIN_SCENE_DURATION, weights[i])

        if i == len(scenes) - 1:
            duration = max(MIN_SCENE_DURATION, round(audio_duration - current, 2))

        end = min(current + duration, audio_duration)

        new_scene = dict(scene)
        new_scene["duration_seconds"] = round(end - current, 2)
        new_scene["tempo"] = f"{int(current)}-{int(end)}"
        new_scene["tempo_inicio"] = round(current, 2)
        new_scene["tempo_fim"] = round(end, 2)
        new_scene["narracao"] = narration_parts[i]

        updated.append(new_scene)
        current = end

    result["cenas"] = updated
    result["audio_duration"] = round(audio_duration, 2)
    result["synced"] = True

    if timeline:
        result = apply_timeline_to_scenes(result, timeline)

    if _should_split_scenes(result):
        result = split_long_scenes(result)
    return ensure_scenes_payload(result)


def _resolve_timeline(
    emotional_timeline: Optional[EmotionalTimeline | dict],
    script: Optional[dict],
    audio_duration: float,
) -> Optional[EmotionalTimeline]:
    if emotional_timeline:
        if isinstance(emotional_timeline, dict):
            timeline = EmotionalTimeline.from_dict(emotional_timeline)
            if not timeline.director_meta.get("synced_to_audio"):
                timeline._compute_timings(audio_duration)
            return timeline
        if isinstance(emotional_timeline, EmotionalTimeline):
            if not emotional_timeline.director_meta.get("synced_to_audio"):
                emotional_timeline._compute_timings(audio_duration)
            return emotional_timeline

    if script:
        return build_emotional_timeline(script, audio_duration=audio_duration)

    return None


def resolve_scene_media(
    assets_root,
    scene_index: int,
    scene_count: int,
):
    """
    Resolve arquivo de mídia para uma cena.
    Prioriza scene-{N} (Visual Media Engine), depois video-{N}, com rotação.
    """

    root = Path(assets_root)
    scene_num = scene_index + 1

    scene_video = root / "videos" / f"scene-{scene_num:02d}.mp4"
    scene_image = root / "images" / f"scene-{scene_num:02d}.jpg"

    if scene_video.exists():
        return scene_video

    if scene_image.exists():
        return scene_image

    videos = sorted((root / "videos").glob("video-*.mp4"))
    images = sorted(
        list((root / "images").glob("imagem-*.jpg"))
        + list((root / "images").glob("imagem-*.jpeg"))
        + list((root / "images").glob("imagem-*.png"))
        + list((root / "images").glob("scene-*.jpg"))
    )

    if scene_index < len(videos):
        return videos[scene_index]

    if videos:
        return videos[scene_index % len(videos)]

    if scene_index < len(images):
        return images[scene_index]

    if images:
        return images[scene_index % len(images)]

    return None


def is_image(path) -> bool:
    return path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
