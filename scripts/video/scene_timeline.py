"""
Timeline de cenas sincronizada com áudio.
"""

from pathlib import Path

from scripts.video.media_probe import probe_duration
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


def sync_scenes_to_audio(
    cenas_data,
    narracao: str,
    audio_path: str,
) -> dict:
    """
    Sincroniza timings das cenas com duração real do áudio.
    Retorna estrutura de cenas atualizada.
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

    weights = [_scene_weight(s) for s in scenes]
    total_weight = sum(weights) or 1

    narration_parts = _split_text_by_weights(narracao, weights)

    current = 0.0
    updated = []

    for i, scene in enumerate(scenes):
        weight = weights[i]
        raw_duration = (weight / total_weight) * audio_duration
        duration = max(3.0, round(raw_duration, 2))

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

    return result


def resolve_scene_media(
    assets_root,
    scene_index: int,
    scene_count: int,
):
    """
    Resolve arquivo de mídia para uma cena.
    Prioriza vídeos; fallback para imagens com rotação se faltarem.
    """

    root = Path(assets_root)
    videos = sorted((root / "videos").glob("video-*.mp4"))
    images = sorted(
        list((root / "images").glob("imagem-*.jpg"))
        + list((root / "images").glob("imagem-*.jpeg"))
        + list((root / "images").glob("imagem-*.png"))
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
