"""
Timeline de cenas sincronizada com áudio e Emotional Timeline.
"""

from pathlib import Path
from typing import Optional

from scripts.core.emotional_timeline import EmotionalTimeline, build_emotional_timeline
from scripts.video.media_probe import probe_duration
from scripts.video.scene_emotion import apply_timeline_to_scenes
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
}

DEFAULT_WEIGHT = 10
TRANSITION_SECONDS = 0.4


def extract_scenes(cenas_data) -> list:
    """Normaliza estrutura de cenas do pipeline."""

    if isinstance(cenas_data, dict):
        return cenas_data.get("cenas", [])

    if isinstance(cenas_data, list):
        return cenas_data

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
        durations.append(max(3.0, round(raw, 2)))

    if durations:
        delta = round(audio_duration - sum(durations), 2)
        durations[-1] = max(3.0, round(durations[-1] + delta, 2))

    return durations


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
        result = dict(cenas_data)
        scenes = list(result.get("cenas", []))
    else:
        result = {"cenas": []}
        scenes = list(cenas_data or [])

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
        return result

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
        duration = durations[i] if i < len(durations) else max(3.0, weights[i])

        if i == len(scenes) - 1:
            duration = max(3.0, round(audio_duration - current, 2))

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

    return result


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
