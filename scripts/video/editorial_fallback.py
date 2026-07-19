"""
Editorial Fallback — composições editoriais quando stock falha.

Ken Burns, parallax, mapas, timelines, gráficos, documentos e montagens.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Optional

from scripts.video.visual_grammar import get_visual_grammar, resolve_editorial_scene_type


def _escape_drawtext(text: str) -> str:
    return text.replace(":", "\\:").replace("'", "\\'").replace("%", "\\%")


def _generate_ken_burns_image(
    source: Path,
    output: Path,
    *,
    duration: float = 5.0,
    zoom: float = 1.15,
    pan: str = "right",
) -> bool:
    """Gera clip Ken Burns a partir de imagem estática."""

    pan_filters = {
        "right": f"zoompan=z='min(zoom+0.001,{zoom})':x='iw/2-(iw/zoom/2)+on*2':y='ih/2-(ih/zoom/2)'",
        "left": f"zoompan=z='min(zoom+0.001,{zoom})':x='iw/2-(iw/zoom/2)-on*2':y='ih/2-(ih/zoom/2)'",
        "in": f"zoompan=z='min(zoom+0.001,{zoom})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    }
    zpan = pan_filters.get(pan, pan_filters["in"])

    frames = int(duration * 30)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(source.resolve()),
        "-vf", (
            f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
            f"{zpan}:d={frames}:s=1920x1080:fps=30"
        ),
        "-t", str(duration),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(output),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output.exists()
    except subprocess.CalledProcessError:
        return False


def _generate_motion_graphic(
    output: Path,
    *,
    overlay_type: str,
    title: str = "",
    subtitle: str = "",
    duration: float = 5.0,
) -> bool:
    """Gera motion graphic editorial via FFmpeg drawtext."""

    safe_title = _escape_drawtext(title[:60] if title else overlay_type.upper())
    safe_sub = _escape_drawtext(subtitle[:80] if subtitle else "")

    bg_colors = {
        "data": "0x0d1117",
        "timeline": "0x1a1a2e",
        "map": "0x16213e",
        "quote": "0x0f0f0f",
        "evidence": "0x1c1c1c",
        "headline": "0x0a0a0a",
    }
    bg = bg_colors.get(overlay_type, "0x1a1a2e")

    filters = [
        f"drawtext=text='{safe_title}':fontcolor=white:fontsize=52:"
        "x=(w-text_w)/2:y=(h-text_h)/2-40:box=1:boxcolor=black@0.5",
    ]
    if safe_sub:
        filters.append(
            f"drawtext=text='{safe_sub}':fontcolor=0xcccccc:fontsize=28:"
            "x=(w-text_w)/2:y=(h-text_h)/2+30"
        )

    if overlay_type == "data":
        filters.append(
            "drawbox=x=200:y=500:w=1520:h=4:color=0x00ff88@0.8:t=fill"
        )
    elif overlay_type == "timeline":
        filters.append(
            "drawbox=x=100:y=h/2:w=w-200:h=3:color=white@0.6:t=fill"
        )
    elif overlay_type == "map":
        filters.append(
            "drawbox=x=760:y=200:w=400:h=300:color=0x2a5298@0.4:t=fill,"
            "drawbox=x=860:y=300:w=8:h=8:color=0xff4444@0.9:t=fill"
        )

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={bg}:s=1920x1080:d={duration}",
        "-vf", ",".join(filters),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(output),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output.exists()
    except subprocess.CalledProcessError:
        return False


def _generate_montage(
    images: list[Path],
    output: Path,
    *,
    duration: float = 5.0,
) -> bool:
    """Montagem rápida de 2-4 imagens."""

    if not images:
        return False

    clip_duration = duration / len(images)
    temp_clips = []
    list_file = output.with_suffix(".txt")

    try:
        for i, img in enumerate(images):
            clip = output.parent / f"_montage_{i}.mp4"
            if not _generate_ken_burns_image(img, clip, duration=clip_duration, zoom=1.12):
                continue
            temp_clips.append(clip)

        if not temp_clips:
            return False

        list_file.write_text(
            "\n".join(f"file '{c.resolve()}'" for c in temp_clips),
            encoding="utf-8",
        )
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output.exists()
    except subprocess.CalledProcessError:
        return False
    finally:
        if list_file.exists():
            list_file.unlink()
        for clip in temp_clips:
            if clip.exists():
                clip.unlink()


def resolve_fallback_plan(scene: dict, query_item: dict) -> dict:
    """Determina plano de fallback editorial baseado na cena."""

    editorial_type = resolve_editorial_scene_type(scene)
    grammar = get_visual_grammar(scene)
    explicit = scene.get("fallback_visual_plan") or query_item.get("fallback_visual_plan")

    if explicit:
        return {"strategy": explicit, "overlay_type": grammar.overlay_type, "editorial_type": editorial_type}

    strategy_map = {
        "data": "animated_chart",
        "timeline": "animated_timeline",
        "map": "animated_map",
        "quote": "document_highlight",
        "evidence": "document_highlight",
        "hook": "ken_burns_montage",
        "turning_point": "ken_burns_aggressive",
        "climax": "montage",
    }

    return {
        "strategy": strategy_map.get(editorial_type, "ken_burns"),
        "overlay_type": grammar.overlay_type,
        "editorial_type": editorial_type,
        "montage_count": grammar.montage_count,
        "zoom_intensity": grammar.zoom_intensity,
    }


def execute_editorial_fallback(
    scene: dict,
    query_item: dict,
    *,
    scene_image: Path,
    scene_video: Path,
    saved_images: Optional[list[Path]] = None,
    duration: float = 5.0,
) -> tuple[bool, str, str]:
    """
    Executa fallback editorial.

    Returns: (success, media_type, strategy_used)
    """

    plan = resolve_fallback_plan(scene, query_item)
    strategy = plan["strategy"]
    title = scene.get("on_screen_text") or query_item.get("busca", "")[:60]
    subtitle = scene.get("narracao", "")[:80]

    # Se temos imagem stock, animar com Ken Burns
    if scene_image.exists() and strategy in ("ken_burns", "ken_burns_aggressive", "ken_burns_montage"):
        zoom = plan.get("zoom_intensity", 1.15)
        pan = "in" if strategy == "ken_burns_aggressive" else "right"
        if _generate_ken_burns_image(scene_image, scene_video, duration=duration, zoom=zoom, pan=pan):
            return True, "editorial_ken_burns", strategy

    # Montagem de imagens disponíveis
    if strategy == "montage" and saved_images:
        imgs = [p for p in saved_images if p.exists()][-plan.get("montage_count", 3):]
        if len(imgs) >= 2 and _generate_montage(imgs, scene_video, duration=duration):
            return True, "editorial_montage", strategy

    # Motion graphics editoriais
    motion_types = ("animated_chart", "animated_timeline", "animated_map", "document_highlight")
    if strategy in motion_types or plan["overlay_type"] in ("data", "timeline", "map", "quote", "evidence", "headline"):
        overlay = plan.get("overlay_type", "data")
        if overlay == "none":
            overlay = "data" if strategy == "animated_chart" else "timeline"
        if _generate_motion_graphic(
            scene_video,
            overlay_type=overlay,
            title=title,
            subtitle=subtitle,
            duration=duration,
        ):
            return True, "editorial_motion", strategy

    # Ken Burns genérico como último recurso editorial
    if scene_image.exists():
        if _generate_ken_burns_image(scene_image, scene_video, duration=duration):
            return True, "editorial_ken_burns", "ken_burns_fallback"

    return False, "none", strategy
