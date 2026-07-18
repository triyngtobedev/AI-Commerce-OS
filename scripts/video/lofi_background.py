"""
Footage de fundo genérico para o template lofi_dark.

Prioridade:
1. Pexels — queries dark/atmosféricas sem relevância temática
2. Biblioteca local reutilizável em assets/lofi_background/
"""

from __future__ import annotations

import shutil
from pathlib import Path

from scripts.video.media_downloader import download_file, select_video_file_with_fallback
from scripts.video.pexels_provider import search_pexels
from scripts.youtube.lofi_dark_config import (
    LOFI_LOCAL_BACKGROUND_DIR,
    lofi_background_query,
)


def _local_background_clips() -> list[Path]:
    if not LOFI_LOCAL_BACKGROUND_DIR.exists():
        return []

    clips: list[Path] = []
    for pattern in ("*.mp4", "*.mov", "*.webm"):
        clips.extend(sorted(LOFI_LOCAL_BACKGROUND_DIR.glob(pattern)))

    return [clip for clip in clips if clip.is_file() and clip.stat().st_size > 10_000]


def _download_pexels_clip(query: str, output_path: Path) -> bool:
    media = search_pexels(query, orientation="landscape")
    if media.get("erro"):
        print(f"[Lofi] Pexels erro: {media['erro']}")
        return False

    videos = media.get("videos") or []
    if not videos:
        print(f"[Lofi] Pexels sem vídeo para: {query}")
        return False

    for video in videos:
        url = select_video_file_with_fallback(video)
        if not url:
            continue
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            download_file(url, output_path)
            if output_path.exists() and output_path.stat().st_size > 10_000:
                return True
        except Exception as exc:
            print(f"[Lofi] Falha ao baixar {query}: {exc}")

    return False


def resolve_lofi_background_clip(
    scene_index: int,
    output_path: Path,
    *,
    reuse_cache: Path | None = None,
) -> Path | None:
    """
    Resolve clip de fundo lofi para uma cena.
    O mesmo clip pode ser reutilizado — comportamento esperado no formato.
    """

    if reuse_cache and reuse_cache.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(reuse_cache, output_path)
        return output_path

    query = lofi_background_query(scene_index)
    if _download_pexels_clip(query, output_path):
        print(f"[Lofi] Footage Pexels: {query} → {output_path.name}")
        return output_path

    local_clips = _local_background_clips()
    if local_clips:
        source = local_clips[scene_index % len(local_clips)]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, output_path)
        print(f"[Lofi] Footage local: {source.name} → {output_path.name}")
        return output_path

    print(f"[Lofi] Nenhum footage disponível para cena {scene_index + 1}")
    return None


def run_lofi_background_pipeline(subject, scenes) -> str:
    """
    Baixa/copia footage genérico para todas as cenas lofi_dark.
    Reutiliza clips quando necessário — aceitável no formato.
    """

    from scripts.utils.slug import content_output_dir

    platform = subject.get("_output_platform", "youtube_dark")
    output_dir = content_output_dir(subject, platform=platform)
    videos_dir = output_dir / "assets" / "videos"
    images_dir = output_dir / "assets" / "images"
    videos_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    scene_list = scenes.get("cenas", []) if isinstance(scenes, dict) else []
    cached_clip: Path | None = None

    for index, _scene in enumerate(scene_list):
        target = videos_dir / f"scene-{index + 1:02d}.mp4"
        if target.exists() and target.stat().st_size > 10_000:
            if cached_clip is None:
                cached_clip = target
            continue

        clip = resolve_lofi_background_clip(
            index,
            target,
            reuse_cache=cached_clip,
        )
        if clip and cached_clip is None:
            cached_clip = clip

        if not clip or not target.exists():
            if cached_clip and cached_clip.exists():
                shutil.copy2(cached_clip, target)
                print(f"[Lofi] Reutilizando clip em cena {index + 1}")
            else:
                print(f"⚠️ [Lofi] Cena {index + 1} sem footage de fundo")

    return "lofi_background"
