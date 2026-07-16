"""
Renderização por cena com duração controlada, motion cinematográfico e transições.

Integrado ao BrandKit para motion por tipo de cena, intro/outro, lower thirds e watermark.
"""

import subprocess
from pathlib import Path

from scripts.core.brand_engine import (
    get_brand_config,
    get_render_style,
    should_show_intro,
    should_show_outro,
    should_show_lower_thirds,
    watermark_filter_for_platform,
)
from scripts.core.brand_kit import get_brand_kit
from scripts.video.subtitle_generator import get_subtitle_ffmpeg_filter
from scripts.video.media_probe import probe_duration
from scripts.video.scene_timeline import (
    extract_scenes,
    resolve_scene_media,
    is_image,
)
from scripts.youtube.brand_overlay import lower_third_filter


def _fade_filter(duration: float, fade: float) -> str:
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
    motion: str = "zoom_in_center",
    fps: int = 30,
    zoom_max: float = 1.14,
) -> str:
    frames = max(1, int(duration * fps))
    zoom_step = (zoom_max - 1.0) / frames

    if motion == "zoom_out_center":
        z_expr = f"max(1.0,zoom-{zoom_step:.6f})"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif motion == "pan_left":
        z_expr = "1.10"
        x_expr = f"max(0,(iw-iw/zoom)*(on/{frames}))"
        y_expr = "ih/2-(ih/zoom/2)"
    elif motion == "pan_right":
        z_expr = "1.10"
        x_expr = f"max(0,(iw-iw/zoom)*(1-on/{frames}))"
        y_expr = "ih/2-(ih/zoom/2)"
    else:
        z_expr = f"min(zoom+{zoom_step:.6f},{zoom_max})"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"

    return (
        f"zoompan=z='{z_expr}':"
        f"x='{x_expr}':y='{y_expr}':"
        f"d={frames}:s={width}x{height}:fps={fps},"
        f"{_scale_pad_filter(width, height)}"
    )


def _video_motion_filter(
    width: int,
    height: int,
    duration: float,
    scene_index: int,
    motion: str = "pan_left",
) -> str:
    """Pan/zoom sutil em vídeos — evita aparência estática."""

    overscale = 1.14
    sw = int(width * overscale)
    sh = int(height * overscale)
    safe_duration = max(duration, 1.0)

    if motion in ("pan_left", "zoom_in_center"):
        crop = (
            f"crop={width}:{height}:"
            f"'(iw-{width})*t/{safe_duration}':'(ih-{height})/2'"
        )
    elif motion in ("pan_right", "zoom_out_center"):
        crop = (
            f"crop={width}:{height}:"
            f"'(iw-{width})*(1-t/{safe_duration})':'(ih-{height})/2'"
        )
    else:
        motions = [
            f"crop={width}:{height}:'(iw-{width})*t/{safe_duration}':'(ih-{height})/2'",
            f"crop={width}:{height}:'(iw-{width})*(1-t/{safe_duration})':'(ih-{height})/2'",
            f"crop={width}:{height}:'(iw-{width})/2':'(ih-{height})*t/{safe_duration}'",
            f"crop={width}:{height}:'(iw-{width})/2':'(ih-{height})*(1-t/{safe_duration})'",
        ]
        crop = motions[scene_index % len(motions)]

    return (
        f"scale={sw}:{sh}:force_original_aspect_ratio=increase,"
        f"crop={sw}:{sh},"
        f"{crop},"
        "setsar=1,fps=30"
    )


def _cinematic_grade(render_style) -> str:
    filters = [render_style.color_grade]
    if render_style.vignette:
        filters.append(render_style.vignette)
    return ",".join(filters)


def _render_card_clip(
    card_path: Path,
    duration: float,
    output_path: Path,
    width: int,
    height: int,
    fade: float,
) -> bool:
    """Renderiza card de intro/outro como clip de vídeo."""

    grade = _cinematic_grade(get_render_style())
    vf = (
        f"{_scale_pad_filter(width, height)},"
        f"{grade},"
        f"{_fade_filter(duration, fade)}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(card_path.resolve()),
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path.exists()
    except subprocess.CalledProcessError:
        return False


def render_scene_clip(
    media_path: Path,
    duration: float,
    output_path: Path,
    width: int = 1920,
    height: int = 1080,
    scene_index: int = 0,
    platform: str = "youtube_dark",
    scene_type: str = "",
    scene_label: str = "",
) -> bool:
    """
    Renderiza clip de duração exata com motion por tipo de cena.
    Lower thirds discretos em hook e revelação.
    """

    render_style = get_render_style(platform)
    kit = get_brand_kit(platform)
    fade = render_style.transition_seconds
    duration = max(2.0, duration)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    grade = _cinematic_grade(render_style)
    motion = kit.motion_for_scene(scene_type, scene_index)

    lower_third = ""
    if (
        should_show_lower_thirds(platform)
        and kit.should_show_lower_third(scene_type)
        and scene_label
    ):
        lower_third = lower_third_filter(scene_label, duration, platform)

    if is_image(media_path):
        vf = (
            f"{_ken_burns_filter(width, height, duration, motion, zoom_max=render_style.ken_burns_zoom_max)},"
            f"{grade},"
            f"{_fade_filter(duration, fade)}"
        )
        if lower_third:
            vf += f",{lower_third}"

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(media_path.resolve()),
            "-t", str(duration),
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-an",
            str(output_path),
        ]

    else:
        source_duration = probe_duration(media_path)
        needs_loop = source_duration > 0 and source_duration < duration - 0.5

        base_vf = _video_motion_filter(width, height, duration, scene_index, motion)
        vf = f"{base_vf},{grade},{_fade_filter(duration, fade)}"
        if lower_third:
            vf += f",{lower_third}"

        cmd = ["ffmpeg", "-y"]

        if needs_loop:
            cmd.extend(["-stream_loop", "-1"])

        start_offset = 0.0
        if source_duration > 2.0:
            start_offset = (scene_index * 1.7) % max(0.5, source_duration - 1.5)

        if start_offset > 0:
            cmd.extend(["-ss", f"{start_offset:.2f}"])

        cmd.extend([
            "-i", str(media_path.resolve()),
            "-t", str(duration),
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "20",
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
    crossfade: float = 0.45,
    scene_types: list | None = None,
    platform: str = "youtube_dark",
) -> bool:
    """Concatena clips com crossfade variável por tipo de cena."""

    if not clip_paths:
        return False

    if len(clip_paths) == 1:
        import shutil
        shutil.copy2(clip_paths[0], output_path)
        return output_path.exists()

    kit = get_brand_kit(platform)

    if crossfade > 0:
        durations = [probe_duration(clip) for clip in clip_paths]
        if all(duration > crossfade for duration in durations):
            crossfades = []
            for index, scene_type in enumerate(scene_types or []):
                crossfades.append(kit.crossfade_for_scene(scene_type))
            if _concat_with_variable_crossfade(
                clip_paths, output_path, crossfades, durations
            ):
                return True

            if _concat_with_crossfade(clip_paths, output_path, crossfade, durations):
                return True

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
        "-crf", "21",
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


def _concat_with_crossfade(
    clip_paths: list,
    output_path: Path,
    crossfade: float,
    durations: list,
) -> bool:
    inputs = []
    for clip in clip_paths:
        inputs.extend(["-i", str(clip.resolve())])

    filter_parts = []
    offset = durations[0] - crossfade

    if len(clip_paths) == 2:
        filter_parts.append(
            f"[0:v][1:v]xfade=transition=fade:duration={crossfade}:offset={offset:.3f}[vout]"
        )
    else:
        filter_parts.append(
            f"[0:v][1:v]xfade=transition=fade:duration={crossfade}:offset={offset:.3f}[v01]"
        )

        accumulated = durations[0] + durations[1] - crossfade
        for index in range(2, len(clip_paths)):
            prev = f"v{index - 1:02d}"
            next_label = f"v{index:02d}" if index < len(clip_paths) - 1 else "vout"
            offset = accumulated - crossfade
            filter_parts.append(
                f"[{prev}][{index}:v]xfade=transition=fade:duration="
                f"{crossfade}:offset={offset:.3f}[{next_label}]"
            )
            accumulated += durations[index] - crossfade

    filter_complex = ";".join(filter_parts)
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "21",
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path.exists()

    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode("utf-8", errors="replace") if error.stderr else ""
        print(f"⚠️ Crossfade falhou, usando concat simples: {stderr[:120]}")
        return False


def _concat_with_variable_crossfade(
    clip_paths: list,
    output_path: Path,
    crossfades: list,
    durations: list,
) -> bool:
    """Crossfade com duração variável entre cenas adjacentes."""

    if len(clip_paths) < 2:
        return False

    inputs = []
    for clip in clip_paths:
        inputs.extend(["-i", str(clip.resolve())])

    filter_parts = []
    cf = crossfades[0] if crossfades else 0.4
    offset = durations[0] - cf
    filter_parts.append(
        f"[0:v][1:v]xfade=transition=fade:duration={cf:.3f}:offset={offset:.3f}[v01]"
    )

    accumulated = durations[0] + durations[1] - cf
    for index in range(2, len(clip_paths)):
        prev = f"v{index - 1:02d}"
        next_label = f"v{index:02d}" if index < len(clip_paths) - 1 else "vout"
        cf = crossfades[index - 1] if index - 1 < len(crossfades) else 0.4
        offset = accumulated - cf
        filter_parts.append(
            f"[{prev}][{index}:v]xfade=transition=fade:duration="
            f"{cf:.3f}:offset={offset:.3f}[{next_label}]"
        )
        accumulated += durations[index] - cf

    filter_complex = ";".join(filter_parts)
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "21",
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path.exists()
    except subprocess.CalledProcessError:
        return False


def render_scenes_video(
    result: dict,
    width: int,
    height: int,
    output_path: Path,
) -> Path | None:
    """Pipeline scene-aware com intro/outro de marca e motion por tipo de cena."""

    from scripts.video.renderer import _resolve_folder

    folder = _resolve_folder(result)
    platform = result.get("platform", "youtube_dark")
    config = get_brand_config(platform)
    kit = config.kit
    scenes = extract_scenes(result.get("cenas", {}))

    if not scenes:
        return None

    assets_root = folder / "assets"
    temp_dir = folder / "assets" / "scene_clips"
    temp_dir.mkdir(parents=True, exist_ok=True)

    clip_paths = []
    scene_types = []
    scene_count = len(scenes)
    topic = result.get("produto", {}).get("nome", "")

    if should_show_intro(platform):
        intro_card = temp_dir / "intro_card.jpg"
        intro_clip = temp_dir / "intro.mp4"
        if kit.render_intro_card(intro_card, topic=topic):
            if _render_card_clip(
                intro_card,
                config.render.intro_seconds,
                intro_clip,
                width,
                height,
                fade=0.6,
            ):
                clip_paths.append(intro_clip)
                scene_types.append("intro")

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
        scene_type = scene.get("tipo", "")
        scene_label = scene.get("visual", "")[:50]

        if not media:
            print(f"⚠️ Sem mídia para cena {i + 1}")
            continue

        clip_out = temp_dir / f"scene_{i + 1:02d}.mp4"

        if render_scene_clip(
            media, duration, clip_out, width, height,
            scene_index=i,
            platform=platform,
            scene_type=scene_type,
            scene_label=scene_label,
        ):
            clip_paths.append(clip_out)
            scene_types.append(scene_type)
            print(f"🎬 Cena {i + 1}/{scene_count} [{scene_type}]: {duration:.1f}s ({media.name})")
        else:
            print(f"⚠️ Falha na cena {i + 1}")

    if should_show_outro(platform):
        outro_card = temp_dir / "outro_card.jpg"
        outro_clip = temp_dir / "outro.mp4"
        if kit.render_outro_card(outro_card, topic=topic):
            if _render_card_clip(
                outro_card,
                config.render.outro_seconds,
                outro_clip,
                width,
                height,
                fade=0.8,
            ):
                clip_paths.append(outro_clip)
                scene_types.append("encerramento")

    if not clip_paths:
        return None

    video_only = temp_dir / "video_track.mp4"
    render_style = get_render_style(platform)

    if not concat_scene_clips(
        clip_paths,
        video_only,
        render_style.crossfade_seconds,
        scene_types=scene_types,
        platform=platform,
    ):
        return None

    return video_only


def mux_video_audio_subtitles(
    video_path: Path,
    audio_path: Path | None,
    subtitle_path: Path | None,
    output_path: Path,
    width: int,
    height: int,
    platform: str = "youtube_dark",
) -> bool:
    """Combina vídeo, áudio e legendas com fade de abertura/encerramento."""

    render_style = get_render_style(platform)
    video_filter = _scale_pad_filter(width, height)

    if subtitle_path and subtitle_path.exists():
        video_filter += f",{get_subtitle_ffmpeg_filter(subtitle_path, platform)}"

    watermark = watermark_filter_for_platform(platform)
    if watermark:
        video_filter += f",{watermark}"

    opening = render_style.opening_fade_seconds
    video_filter += f",fade=t=in:st=0:d={opening}"

    audio_duration = 0.0
    if audio_path and audio_path.exists():
        audio_duration = probe_duration(audio_path)

    has_audio = audio_path and audio_path.exists() and audio_path.stat().st_size > 0
    audio_delay = _audio_delay(platform) if has_audio else 0.0
    closing = render_style.closing_fade_seconds
    fade_start = 0.0

    if audio_duration > closing + 1:
        fade_start = max(0.0, audio_delay + audio_duration - closing)
        video_filter += f",fade=t=out:st={fade_start:.2f}:d={closing}"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
    ]

    if has_audio:
        if audio_delay > 0:
            cmd.extend(["-itsoffset", f"{audio_delay:.3f}"])
        cmd.extend(["-i", str(audio_path.resolve())])

    cmd.extend([
        "-vf", video_filter,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "21",
        "-pix_fmt", "yuv420p",
    ])

    if has_audio:
        af = f"afade=t=in:st=0:d={opening}"
        if audio_duration > closing + 1:
            af += f",afade=t=out:st={audio_duration - closing:.2f}:d={closing}"
        cmd.extend([
            "-af", af,
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


def _audio_delay(platform: str) -> float:
    """Atraso do áudio para alinhar narração com cenas após intro visual."""

    if not should_show_intro(platform):
        return 0.0

    return get_render_style(platform).intro_seconds
