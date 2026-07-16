"""
Renderização por cena com duração controlada, motion e transições.
"""

import subprocess
from pathlib import Path

from scripts.core.brand_profile import get_brand
from scripts.youtube.brand_overlay import watermark_filter
from scripts.video.media_probe import probe_duration, probe_has_video_stream
from scripts.video.scene_timeline import (
    extract_scenes,
    resolve_scene_media,
    is_image,
    TRANSITION_SECONDS,
)


def _fade_filter(duration: float, fade: float = TRANSITION_SECONDS) -> str:
    fade_out = max(0, duration - fade)
    return (
        f"fade=t=in:st=0:d={fade},"
        f"fade=t=out:st={fade_out}:d={fade}"
    )


def _scale_pad_filter(width: int, height: int) -> str:
    return (
        f"scale={width}:{height}:"
        "force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
    )


def _ken_burns_filter(
    width: int,
    height: int,
    duration: float,
    fps: int = 30,
) -> str:
    frames = max(1, int(duration * fps))
    return (
        f"zoompan=z='min(zoom+0.0006,1.2)':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={width}x{height}:fps={fps},"
        f"{_scale_pad_filter(width, height)}"
    )


def render_scene_clip(
    media_path: Path,
    duration: float,
    output_path: Path,
    width: int = 1920,
    height: int = 1080,
) -> bool:
    """
    Renderiza um clip de duração exata a partir de vídeo ou imagem.
    Vídeos curtos são loopados; imagens recebem Ken Burns.
    """

    duration = max(2.0, duration)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if is_image(media_path):
        vf = (
            f"{_ken_burns_filter(width, height, duration)},"
            f"{_fade_filter(duration)}"
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(media_path.resolve()),
            "-t", str(duration),
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-an",
            str(output_path),
        ]

    else:
        source_duration = probe_duration(media_path)
        needs_loop = source_duration < duration - 0.5

        base_vf = _scale_pad_filter(width, height)
        vf = f"{base_vf},{_fade_filter(duration)}"

        cmd = ["ffmpeg", "-y"]

        if needs_loop:
            cmd.extend(["-stream_loop", "-1"])

        cmd.extend([
            "-i", str(media_path.resolve()),
            "-t", str(duration),
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-an",
            str(output_path),
        ])

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path.exists()

    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode("utf-8", errors="replace") if error.stderr else ""
        print(f"❌ Erro renderizando cena ({media_path.name}): {stderr[:200]}")
        return False


def concat_scene_clips(
    clip_paths: list,
    output_path: Path,
) -> bool:
    """Concatena clips de cena sem re-encode quando possível."""

    if not clip_paths:
        return False

    list_file = output_path.parent / "scene_concat.txt"

    with open(list_file, "w", encoding="utf-8") as file:
        for clip in clip_paths:
            path = str(clip.resolve()).replace("\\", "/")
            file.write(f"file '{path}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path.exists()

    except subprocess.CalledProcessError:
        return _concat_scene_clips_reencode(clip_paths, output_path)


def _concat_scene_clips_reencode(clip_paths, output_path) -> bool:
    """Fallback: re-encode na concatenação."""

    list_file = output_path.parent / "scene_concat.txt"

    with open(list_file, "w", encoding="utf-8") as file:
        for clip in clip_paths:
            path = str(clip.resolve()).replace("\\", "/")
            file.write(f"file '{path}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path.exists()

    except subprocess.CalledProcessError as error:
        print(f"❌ Erro concatenando cenas: {error}")
        return False


def render_scenes_video(
    result: dict,
    width: int,
    height: int,
    output_path: Path,
) -> Path | None:
    """
    Pipeline scene-aware: uma mídia por cena, duração sincronizada.
    """

    from scripts.video.renderer import _resolve_folder

    folder = _resolve_folder(result)
    scenes = extract_scenes(result.get("cenas", {}))

    if not scenes:
        return None

    assets_root = folder / "assets"
    temp_dir = folder / "assets" / "scene_clips"
    temp_dir.mkdir(parents=True, exist_ok=True)

    clip_paths = []
    scene_count = len(scenes)

    for i, scene in enumerate(scenes):
        duration = scene.get("duration_seconds")

        if not duration:
            tempo = scene.get("tempo", "0-5")
            try:
                start, end = tempo.split("-")
                duration = float(end) - float(start)
            except ValueError:
                duration = 5.0

        media = resolve_scene_media(assets_root, i, scene_count)

        if not media:
            print(f"⚠️ Sem mídia para cena {i + 1}")
            continue

        clip_out = temp_dir / f"scene_{i + 1:02d}.mp4"

        if render_scene_clip(media, duration, clip_out, width, height):
            clip_paths.append(clip_out)
            print(f"🎬 Cena {i + 1}/{scene_count}: {duration:.1f}s ({media.name})")
        else:
            print(f"⚠️ Falha na cena {i + 1}")

    if not clip_paths:
        return None

    video_only = temp_dir / "video_track.mp4"

    if not concat_scene_clips(clip_paths, video_only):
        return None

    return video_only


def mux_video_audio_subtitles(
    video_path: Path,
    audio_path: Path | None,
    subtitle_path: Path | None,
    output_path: Path,
    width: int,
    height: int,
) -> bool:
    """Combina vídeo, áudio e legendas no arquivo final."""

    video_filter = _scale_pad_filter(width, height)

    if subtitle_path and subtitle_path.exists():
        sub = subtitle_path.resolve().as_posix().replace(":", "\\:")
        video_filter += (
            f",subtitles='{sub}':force_style="
            "'FontName=Arial,FontSize=22,PrimaryColour=&HFFFFFF,"
            "OutlineColour=&H000000,Outline=2,Shadow=1,MarginV=40'"
        )

    platform = "youtube_dark"
    video_filter += f",{watermark_filter(get_brand(platform))}"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
    ]

    has_audio = audio_path and audio_path.exists() and audio_path.stat().st_size > 0

    if has_audio:
        cmd.extend(["-i", str(audio_path.resolve())])

    cmd.extend([
        "-vf", video_filter,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
    ])

    if has_audio:
        cmd.extend([
            "-c:a", "aac",
            "-b:a", "192k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
        ])
    else:
        cmd.append("-an")

    cmd.extend([
        "-movflags", "+faststart",
        str(output_path),
    ])

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path.exists()

    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode("utf-8", errors="replace") if error.stderr else ""
        print(f"❌ Erro no mux final: {stderr[:300]}")
        return False
