"""
Thumbnail Generator para YouTube.

Seleciona mídia estratégica (não frame aleatório) e aplica layout CTR via BrandKit.
"""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.core.brand_kit import get_brand_kit, score_image_contrast
from scripts.utils.slug import content_output_dir
from scripts.video.scene_timeline import resolve_scene_media, extract_scenes, is_image


THUMBNAIL_SCENE_PRIORITY = ["hook", "revelacao", "impacto", "desenvolvimento_1"]


def _find_scene_index_by_type(scenes: list, scene_type: str) -> Optional[int]:
    for index, scene in enumerate(scenes):
        if scene.get("tipo") == scene_type:
            return index
    return None


def _collect_scene_media(folder: Path, scenes: list) -> List[Path]:
    """Coleta mídia das cenas prioritárias para thumbnail."""

    assets_root = folder / "assets"
    scene_count = len(scenes)
    candidates: List[Path] = []

    for scene_type in THUMBNAIL_SCENE_PRIORITY:
        index = _find_scene_index_by_type(scenes, scene_type)
        if index is None:
            continue
        media = resolve_scene_media(assets_root, index, scene_count)
        if media and media.exists():
            candidates.append(media)

    for index in range(scene_count):
        media = resolve_scene_media(assets_root, index, scene_count)
        if media and media.exists() and media not in candidates:
            candidates.append(media)

    images = folder / "assets" / "images"
    if images.exists():
        for img in sorted(images.glob("scene-*.jpg")):
            if img not in candidates:
                candidates.append(img)

    videos = folder / "assets" / "videos"
    if videos.exists():
        for vid in sorted(videos.glob("scene-*.mp4")):
            if vid not in candidates:
                candidates.append(vid)

    return candidates


def _extract_frame(
    video_path: Path,
    output_path: Path,
    timestamp: str = "00:00:02",
) -> bool:
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", timestamp,
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", "2",
                str(output_path),
            ],
            check=True,
            capture_output=True,
        )
        return output_path.exists()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _pick_best_hero_image(
    folder: Path,
    scenes: Optional[dict],
    video_path: Optional[str],
) -> Optional[Path]:
    """
    Seleciona a melhor imagem hero por contraste.
    Prioriza mídia de cenas hook/revelação — evita frame aleatório do vídeo final.
    """

    frame_dir = folder / "assets" / "thumbnail_candidates"
    frame_dir.mkdir(parents=True, exist_ok=True)

    scene_list = extract_scenes(scenes or {})
    candidates: List[Path] = []

    if scene_list:
        candidates.extend(_collect_scene_media(folder, scene_list))

    if not candidates and video_path:
        for ts in ("00:00:03", "00:00:08", "00:00:15"):
            frame_path = frame_dir / f"frame_{ts.replace(':', '')}.jpg"
            if _extract_frame(Path(video_path), frame_path, ts):
                candidates.append(frame_path)

    if not candidates:
        return None

    scored = [(score_image_contrast(path), path) for path in candidates]

    for score, path in scored:
        if is_image(path):
            return path

    best_video = max(scored, key=lambda item: item[0])[1]
    frame_path = frame_dir / "best_frame.jpg"
    if _extract_frame(best_video, frame_path, "00:00:01"):
        return frame_path

    return best_video if is_image(best_video) else None


def _derive_hook_text(
    content: Dict[str, Any],
    strategy: Optional[dict],
) -> str:
    hook = (
        content.get("thumbnail_texto")
        or (strategy or {}).get("gancho", "")
        or content.get("titulo", "")
    )

    words = hook.strip().split()
    if len(words) > 4:
        hook = " ".join(words[:4])

    return hook.strip() or "DOCUMENTÁRIO"


def generate_thumbnail(
    subject: Dict[str, Any],
    content: Dict[str, Any],
    video_path: Optional[str] = None,
    platform: str = "youtube_dark",
    scenes: Optional[dict] = None,
    strategy: Optional[dict] = None,
) -> Optional[str]:
    """Gera thumbnail CTR com layout consistente via BrandKit."""

    folder = content_output_dir(subject, platform=platform)
    folder.mkdir(parents=True, exist_ok=True)

    thumbnail_path = folder / "thumbnail.jpg"
    kit = get_brand_kit(platform)

    hook_text = _derive_hook_text(content, strategy)
    topic = subject.get("nome", content.get("titulo", ""))[:50]

    hero = _pick_best_hero_image(folder, scenes, video_path)

    if hero:
        if kit.compose_thumbnail(hero, hook_text, thumbnail_path, topic=topic):
            print(f"🖼️ Thumbnail CTR gerada: {thumbnail_path}")
            return str(thumbnail_path)

    try:
        from PIL import Image

        frame_path = folder / "thumbnail_frame.jpg"
        img = Image.new("RGB", (1280, 720), color=kit.colors.primary)
        img.save(frame_path, "JPEG")

        if kit.compose_thumbnail(frame_path, hook_text, thumbnail_path, topic=topic):
            print(f"🖼️ Thumbnail placeholder com marca: {thumbnail_path}")
            return str(thumbnail_path)

    except ImportError:
        print("⚠️ Pillow não disponível. Thumbnail não gerada.")

    return None
