"""
Thumbnail Generator para YouTube.

Seleciona mídia estratégica (não frame aleatório) e aplica layout CTR via BrandKit.
"""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.core.brand_kit import get_brand_kit, score_image_contrast
from scripts.youtube.lofi_dark_config import LOFI_THUMBNAIL_QUERIES, is_lofi_dark
from scripts.video.pexels_provider import search_pexels
from scripts.video.media_downloader import download_file
from scripts.utils.slug import content_output_dir
from scripts.video.media_probe import probe_duration
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


def _video_frame_timestamp(video_path: Path) -> str:
    """Escolhe timestamp dramático (~30% do vídeo) para frame de thumbnail."""

    duration = probe_duration(str(video_path))
    if duration <= 0:
        return "00:00:02"
    target = max(1.0, min(duration * 0.3, duration - 0.5))
    minutes = int(target // 60)
    seconds = int(target % 60)
    return f"00:{minutes:02d}:{seconds:02d}"


def _extract_frame(
    video_path: Path,
    output_path: Path,
    timestamp: str | None = None,
) -> bool:
    ts = timestamp or _video_frame_timestamp(video_path)
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", ts,
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", "2",
                str(output_path),
            ],
            check=True,
            capture_output=True,
        )
        return output_path.exists() and output_path.stat().st_size > 1024
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
        print("⚠️ Thumbnail: nenhuma hero image encontrada nas cenas ou no vídeo")
        return None

    scored = [(score_image_contrast(path), path) for path in candidates]
    scored.sort(key=lambda item: item[0], reverse=True)

    for score, path in scored:
        if is_image(path) and score >= 20:
            return path

    best_video = scored[0][1] if scored else None
    if best_video and not is_image(best_video):
        frame_path = frame_dir / "best_frame.jpg"
        if _extract_frame(best_video, frame_path):
            return frame_path

    for score, path in scored:
        if is_image(path):
            return path

    return None


def _generate_brand_background(
    kit,
    folder: Path,
    topic: str,
) -> Optional[Path]:
    """Gera fundo de marca (gradiente radial) como fallback sem hero image."""

    background_path = folder / "thumbnail_brand_bg.jpg"

    if kit.render_thumbnail_background(background_path, topic=topic):
        print(f"🖼️ Thumbnail: usando fundo de marca (BrandKit): {background_path}")
        return background_path

    print("⚠️ Thumbnail: falha ao gerar fundo de marca via BrandKit")
    return None


def _derive_hook_text(
    content: Dict[str, Any],
    strategy: Optional[dict],
) -> str:
    hook = (
        content.get("thumbnail_texto")
        or (strategy or {}).get("gancho", "")
        or content.get("titulo", "")
    )

    if is_lofi_dark((strategy or {}).get("roteiro_template")):
        words = hook.strip().split()
        if len(words) > 6:
            hook = " ".join(words[:6])
        return hook.strip() or "para refletir"

    words = hook.strip().split()
    if len(words) > 4:
        hook = " ".join(words[:4])

    return hook.strip() or "DOCUMENTÁRIO"


def _fetch_lofi_hero_image(folder: Path) -> Optional[Path]:
    """Busca imagem anime/arte digital no Pexels para thumbnail lofi."""

    frame_dir = folder / "assets" / "thumbnail_candidates"
    frame_dir.mkdir(parents=True, exist_ok=True)

    for index, query in enumerate(LOFI_THUMBNAIL_QUERIES):
        media = search_pexels(query, orientation="landscape")
        photos = media.get("photos") or []
        for photo in photos[:3]:
            src = photo.get("src") or {}
            url = src.get("large2x") or src.get("large") or src.get("original")
            if not url:
                continue
            target = frame_dir / f"lofi_hero_{index}.jpg"
            try:
                download_file(url, target)
                if target.exists() and target.stat().st_size > 2048:
                    return target
            except Exception:
                continue

    return None


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
    roteiro_template = (strategy or {}).get("roteiro_template", "")
    kit = get_brand_kit(platform, roteiro_template=roteiro_template)
    lofi = is_lofi_dark(roteiro_template)

    hook_text = _derive_hook_text(content, strategy)
    topic = subject.get("nome", content.get("titulo", ""))[:50]

    hero = _pick_best_hero_image(folder, scenes, video_path)
    if lofi and not hero:
        hero = _fetch_lofi_hero_image(folder)

    if hero:
        compose = kit.compose_thumbnail_lofi if lofi else kit.compose_thumbnail
        if compose(hero, hook_text, thumbnail_path, topic=topic):
            if thumbnail_path.exists() and thumbnail_path.stat().st_size > 2048:
                print(f"🖼️ Thumbnail CTR gerada: {thumbnail_path}")
                return str(thumbnail_path)
        print(
            f"⚠️ Thumbnail: falha ao compor thumbnail com hero image "
            f"({hero}) — tentando fallback de marca"
        )
    else:
        print("⚠️ Thumbnail: sem hero image — usando fallback de marca")

    background = _generate_brand_background(kit, folder, topic)
    compose = kit.compose_thumbnail_lofi if lofi else kit.compose_thumbnail
    if background and compose(
        background,
        hook_text,
        thumbnail_path,
        topic=topic,
    ):
        print(f"🖼️ Thumbnail CTR gerada (fallback marca): {thumbnail_path}")
        return str(thumbnail_path)

    print("⚠️ Thumbnail: falha ao compor thumbnail mesmo com fallback de marca")

    try:
        from PIL import Image

        frame_path = folder / "thumbnail_frame.jpg"
        img = Image.new("RGB", (1280, 720), color=kit.colors.primary)
        img.save(frame_path, "JPEG")

        if compose(frame_path, hook_text, thumbnail_path, topic=topic):
            print(f"🖼️ Thumbnail placeholder com marca: {thumbnail_path}")
            return str(thumbnail_path)

        print("⚠️ Thumbnail: falha ao compor placeholder sólido")

    except ImportError:
        print("⚠️ Pillow não disponível. Thumbnail não gerada.")

    return None
