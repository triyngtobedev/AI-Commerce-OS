"""
Thumbnail Generator para YouTube.

Gera thumbnail com frame estratégico + overlay de marca.
"""

import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from scripts.utils.slug import content_output_dir
from scripts.youtube.brand_overlay import apply_brand_thumbnail


def _pick_frame_timestamp(scenes_data: Optional[dict] = None) -> str:
    """
    Seleciona timestamp do hook visual (primeira cena).
    """

    if not scenes_data:
        return "00:00:02"

    scenes = scenes_data.get("cenas", []) if isinstance(scenes_data, dict) else []

    if scenes:
        inicio = scenes[0].get("tempo_inicio")
        if inicio is not None:
            seconds = max(1, int(float(inicio) + 1))
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins:02d}:{secs:02d}:00"

        tempo = scenes[0].get("tempo", "0-5")
        try:
            start, _ = tempo.split("-")
            seconds = max(1, int(start) + 1)
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins:02d}:{secs:02d}:00"
        except ValueError:
            pass

    return "00:00:02"


def _extract_frame(
    video_path: Path,
    output_path: Path,
    timestamp: str = "00:00:02",
) -> bool:
    """Extrai um frame do vídeo via FFmpeg."""

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


def generate_thumbnail(
    subject: Dict[str, Any],
    content: Dict[str, Any],
    video_path: Optional[str] = None,
    platform: str = "youtube_dark",
    scenes: Optional[dict] = None,
    strategy: Optional[dict] = None,
) -> Optional[str]:
    """
    Gera thumbnail profissional para vídeo YouTube.
    """

    folder = content_output_dir(subject, platform=platform)
    folder.mkdir(parents=True, exist_ok=True)

    thumbnail_path = folder / "thumbnail.jpg"

    hook_text = (
        content.get("thumbnail_texto")
        or (strategy or {}).get("gancho", "")
        or content.get("titulo", "")
    )

    subtitle = subject.get("nome", "")[:50]
    timestamp = _pick_frame_timestamp(scenes)

    if video_path:
        frame_path = folder / "thumbnail_frame.jpg"

        if _extract_frame(Path(video_path), frame_path, timestamp):
            if apply_brand_thumbnail(
                frame_path,
                hook_text,
                thumbnail_path,
                subtitle=subtitle,
            ):
                print(f"🖼️ Thumbnail gerada: {thumbnail_path}")
                return str(thumbnail_path)

            frame_path.rename(thumbnail_path)
            return str(thumbnail_path)

    try:
        from PIL import Image

        frame_path = folder / "thumbnail_frame.jpg"
        img = Image.new("RGB", (1280, 720), color=(12, 18, 32))
        img.save(frame_path, "JPEG")

        if apply_brand_thumbnail(
            frame_path,
            hook_text,
            thumbnail_path,
            subtitle=subtitle,
        ):
            print(f"🖼️ Thumbnail placeholder com marca: {thumbnail_path}")
            return str(thumbnail_path)

    except ImportError:
        print("⚠️ Pillow não disponível. Thumbnail não gerada.")

    return None
