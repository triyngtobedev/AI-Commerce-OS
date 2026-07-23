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
from scripts.video.media_probe import probe_duration
from scripts.video.scene_timeline import (
    extract_scenes,
    resolve_scene_media,
    is_image,
)
from scripts.video.scene_emotion import get_scene_render_hints
from scripts.video.subtitle_generator import get_subtitle_ffmpeg_filter
from scripts.youtube.brand_overlay import lower_third_filter


MAX_AV_SYNC_DELTA = 0.5


class RenderSyncError(RuntimeError):
    """Diferença áudio/vídeo acima do limite permitido."""


def get_file_duration(path: str | Path) -> float:
    """Obtém duração de arquivo de mídia via FFprobe."""
    import json
    import subprocess

    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", str(path)],
            capture_output=True, text=True, timeout=15,
        )
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception:
        return 0.0


def _scene_duration(scene: dict, synced: bool) -> float:
    """Obtém duração da cena — fallback silencioso para não quebrar o pipeline."""

    duration = scene.get("duration_seconds")
    if duration and float(duration) > 0:
        return float(duration)

    if synced:
        print(
            f"[Render] ⚠️ Cena '{scene.get('tipo', '?')}' sem duration_seconds "
            f"— estimando pelo tempo/áudio"
        )

    tempo = scene.get("tempo", "0-5")
    try:
        start, end = tempo.split("-")
        return max(2.0, float(end) - float(start))
    except ValueError:
        return 5.0


def _validate_scene_coverage(scenes: list, clip_count: int) -> None:
    if clip_count < len(scenes):
        raise RenderSyncError(
            f"Render incompleto: {clip_count}/{len(scenes)} cenas renderizadas"
        )


def compute_expected_video_duration(
    platform: str,
    scenes: list,
    *,
    synced: bool = True,
    narration_duration: float | None = None,
) -> float:
    """
    Duração alvo do trilho de vídeo: intro + cenas sincronizadas + outro.

    Deve coincidir com a duração do áudio de narração na porção central
    (intro/outro são padding visual de marca).
    """

    intro = 0.0
    outro = 0.0
    if should_show_intro(platform):
        intro = get_render_style(platform).intro_seconds
    if should_show_outro(platform):
        outro = get_render_style(platform).outro_seconds

    if narration_duration is not None and narration_duration > 0:
        content = narration_duration
    else:
        content = sum(_scene_duration(scene, synced) for scene in scenes)

    return intro + content + outro


def validate_av_sync(
    video_path: Path,
    audio_path: Path | None,
    *,
    audio_offset: float = 0.0,
    outro_seconds: float = 0.0,
    max_delta: float = MAX_AV_SYNC_DELTA,
) -> float:
    """
    Valida sincronia entre vídeo final e narração.

    O vídeo deve terminar em audio_offset + audio_duration + outro_seconds
    (intro antes da narração, outro depois). Retorna o delta absoluto.
    """

    video_duration = probe_duration(video_path)
    audio_duration = probe_duration(audio_path) if audio_path and audio_path.exists() else 0.0

    if audio_duration <= 0:
        return 0.0

    narration_end = audio_offset + audio_duration
    expected_video = narration_end + outro_seconds
    delta = abs(video_duration - expected_video)

    if video_duration + max_delta < narration_end:
        raise RenderSyncError(
            f"Narração ultrapassa o vídeo: vídeo={video_duration:.2f}s < "
            f"fim da narração={narration_end:.2f}s (offset={audio_offset:.2f}s)"
        )

    if delta > max_delta:
        raise RenderSyncError(
            f"Dessincronia áudio/vídeo: vídeo={video_duration:.2f}s, "
            f"esperado={expected_video:.2f}s "
            f"(offset={audio_offset:.2f}s + áudio={audio_duration:.2f}s + "
            f"outro={outro_seconds:.2f}s), delta={delta:.2f}s"
        )

    return delta


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


def _clip_normalize_filter(width: int, height: int) -> str:
    """Normaliza resolução, formato de cor e FPS antes do xfade."""

    return (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},format=yuv420p,fps=30"
    )


def _normalize_input_filters(clip_count: int, width: int, height: int) -> list[str]:
    norm = _clip_normalize_filter(width, height)
    return [f"[{index}:v]{norm}[n{index:02d}]" for index in range(clip_count)]


def _run_ffmpeg(
    cmd: list,
    *,
    context: str = "",
    output_path: Path | None = None,
) -> bool:
    """Executa FFmpeg e imprime stderr completo em caso de falha."""

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode("utf-8", errors="replace") if error.stderr else ""
        label = f" ({context})" if context else ""
        print(f"❌ FFmpeg falhou{label}:")
        if stderr:
            print(stderr)
        else:
            print(f"  código de saída: {error.returncode}")
        return False

    if output_path is not None:
        return output_path.exists()
    return True


def _ease_in_out(t: float) -> float:
    """Cubic ease-in-out: suave no início e no fim, aceleração no meio."""
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0


def _ken_burns_filter(
    width: int,
    height: int,
    duration: float,
    motion: str = "zoom_in_center",
    fps: int = 30,
    zoom_max: float = 1.25,
) -> str:
    """Ken Burns com easing cúbico — movimento cinematográfico suave."""

    frames = max(1, int(duration * fps))
    zoom_range = zoom_max - 1.0
    base_zoom = min(1.06, zoom_max - 0.06)

    # Easing cúbico: zoom acelera e desacelera suavemente
    # zoom(t) = 1.0 + zoom_range * ease_in_out(t/duration)
    z_expr = (
        f"1+{zoom_range:.4f}*"
        f"if(lt(on/{frames},0.5),"
        f"4*((on/{frames})^3),"
        f"1-((-2*(on/{frames})+2)^3)/2)"
    )

    # Movimentos com easing suave
    if motion == "zoom_out_center":
        z_expr = (
            f"1+{zoom_range:.4f}*"
            f"(1-if(lt(on/{frames},0.5),"
            f"4*((on/{frames})^3),"
            f"1-((-2*(on/{frames})+2)^3)/2))"
        )
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif motion == "pan_left":
        z_expr = f"{base_zoom + 0.04:.2f}"
        x_expr = f"max(0,(iw-iw/zoom)*((on/{frames})^2))"
        y_expr = f"max(0,(ih-ih/zoom)*(0.5+0.12*sin(on/{max(frames, 1)})))"
    elif motion == "pan_right":
        z_expr = f"{base_zoom + 0.04:.2f}"
        x_expr = f"max(0,(iw-iw/zoom)*(1-((on/{frames})^2)))"
        y_expr = f"max(0,(ih-ih/zoom)*(0.5-0.12*sin(on/{max(frames, 1)})))"
    elif motion == "parallax_left":
        z_expr = f"1+{zoom_range * 0.7:.4f}*if(lt(on/{frames},0.5),4*((on/{frames})^3),1-((-2*(on/{frames})+2)^3)/2)"
        x_expr = f"max(0,(iw-iw/zoom)*((on/{frames})^2))"
        y_expr = f"max(0,(ih-ih/zoom)*(on/({frames * 2})))"
    elif motion == "parallax_right":
        z_expr = f"1+{zoom_range * 0.7:.4f}*if(lt(on/{frames},0.5),4*((on/{frames})^3),1-((-2*(on/{frames})+2)^3)/2)"
        x_expr = f"max(0,(iw-iw/zoom)*(1-((on/{frames})^2)))"
        y_expr = f"max(0,(ih-ih/zoom)*(1-(on/({frames * 2}))))"
    elif motion == "drift_up":
        z_expr = f"{base_zoom:.2f}"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = f"max(0,(ih-ih/zoom)*(1-((on/{frames})^2)))"
    elif motion == "drift_down":
        z_expr = f"{base_zoom:.2f}"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = f"max(0,(ih-ih/zoom)*((on/{frames})^2))"
    else:
        z_expr = (
            f"1+{zoom_range:.4f}*"
            f"if(lt(on/{frames},0.5),"
            f"4*((on/{frames})^3),"
            f"1-((-2*(on/{frames})+2)^3)/2)"
        )
        x_expr = "iw/2-(iw/zoom/2)+8*sin(on/30)"
        y_expr = "ih/2-(ih/zoom/2)+5*sin(on/45)"

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
    """Pan/zoom/parallax em vídeos — movimento constante, nunca estático.

    Seguro para qualquer resolução de entrada: normaliza primeiro para
    `width x height` antes de aplicar o crop dinâmico.
    """

    safe_duration = max(duration, 1.0)

    # Normaliza o vídeo de entrada para o tamanho-alvo com overscale de 1.18
    # ANTES de qualquer crop — garante que iw/ih sejam sempre maiores que width/height
    overscale = 1.18
    sw = int(width * overscale)
    sh = int(height * overscale)
    normalize = (
        f"scale={sw}:{sh}:force_original_aspect_ratio=increase,"
        f"crop={sw}:{sh}"
    )

    # Offsets de crop dentro do frame já normalizado (sw x sh)
    # iw={sw}, ih={sh} agora — sempre maiores que width/height
    dx = sw - width   # pixels disponíveis horizontalmente
    dy = sh - height  # pixels disponíveis verticalmente

    if motion in ("pan_left", "zoom_in_center", "parallax_left"):
        crop = (
            f"crop={width}:{height}:"
            f"'{dx}*t/{safe_duration}':"
            f"'{dy}*(0.35+0.3*t/{safe_duration})'"
        )
    elif motion in ("pan_right", "zoom_out_center", "parallax_right"):
        crop = (
            f"crop={width}:{height}:"
            f"'{dx}*(1-t/{safe_duration})':"
            f"'{dy}*(0.65-0.3*t/{safe_duration})'"
        )
    elif motion in ("drift_up",):
        crop = (
            f"crop={width}:{height}:"
            f"'{dx}/2':"
            f"'{dy}*(1-t/{safe_duration})'"
        )
    elif motion in ("drift_down",):
        crop = (
            f"crop={width}:{height}:"
            f"'{dx}/2':"
            f"'{dy}*t/{safe_duration}'"
        )
    else:
        motions = [
            f"crop={width}:{height}:'{dx}*t/{safe_duration}':'{dy}*(0.35+0.3*t/{safe_duration})'",
            f"crop={width}:{height}:'{dx}*(1-t/{safe_duration})':'{dy}*(0.65-0.3*t/{safe_duration})'",
            f"crop={width}:{height}:'{dx}/2':'{dy}*t/{safe_duration}'",
            f"crop={width}:{height}:'{dx}/2':'{dy}*(1-t/{safe_duration})'",
        ]
        crop = motions[scene_index % len(motions)]

    return f"{normalize},{crop},setsar=1,fps=30"


def _lofi_grade_filter() -> str:
    """Footage de fundo levemente escurecido (~70% de opacidade visual)."""

    return "eq=brightness=-0.14:contrast=0.94:saturation=0.88"


def _is_lofi_scene(scene: dict | None) -> bool:
    if not scene:
        return False
    return scene.get("render_profile") == "lofi_dark"


def _cinematic_grade(render_style, *, lofi: bool = False) -> str:
    if lofi:
        return _lofi_grade_filter()
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
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode("utf-8", errors="replace") if error.stderr else ""
        print("❌ FFmpeg falhou (intro card):")
        if stderr.strip():
            print(stderr)
        else:
            print(f"  código de saída: {error.returncode}")
        return False


def _video_needs_upscale(media_path: Path, target_width: int, target_height: int) -> bool:
    """Retorna True se o vídeo é menor que o target em qualquer dimensão."""
    import json
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "json",
                str(media_path),
            ],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(result.stdout)
        stream = (data.get("streams") or [{}])[0]
        w = stream.get("width", 0)
        h = stream.get("height", 0)
        return (w > 0 and w < target_width) or (h > 0 and h < target_height)
    except Exception:
        return False  # seguro: assume que não precisa


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
    scene: dict | None = None,
) -> bool:
    """
    Renderiza clip de duração exata com motion por tipo de cena.
    Consome hints emocionais quando scene contém emotion/intensity/timeline.
    """

    render_style = get_render_style(platform)
    kit = get_brand_kit(platform)
    fade = render_style.transition_seconds
    duration = max(2.0, duration)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    hints = get_scene_render_hints(scene or {"tipo": scene_type})
    lofi = _is_lofi_scene(scene)

    grammar = (scene or {}).get("visual_grammar", {})
    if grammar:
        motion = grammar.get("camera_move", hints.get("motion", "slow_push"))
        zoom_max = grammar.get("zoom_intensity", render_style.ken_burns_zoom_max)
        fade = grammar.get("crossfade", render_style.transition_seconds)
    else:
        motion = "slow_pan" if lofi else (
            hints.get("motion") or kit.motion_for_scene(scene_type, scene_index)
        )
        zoom_max = 1.02 if lofi else (
            render_style.ken_burns_zoom_max * (1.0 + hints.get("zoom_intensity", 0.0))
        )
        fade = 1.2 if lofi else render_style.transition_seconds

    grade = _cinematic_grade(render_style, lofi=lofi)

    lower_third = ""
    if (
        not lofi
        and should_show_lower_thirds(platform)
        and kit.should_show_lower_third(scene_type)
        and scene_label
    ):
        lower_third = lower_third_filter(scene_label, duration, platform)

    # ── Overlay escuro + título centralizado (dark documentary) ─────
    _raw_title = (scene or {}).get("title", "") or scene_label
    _fade_out_start = max(0.0, duration - 0.5)
    _overlay_parts = ["colorchannelmixer=aa=0.25"]

    if _raw_title:
        _safe = str(_raw_title).strip().replace("'", "\\'").replace(":", "\\:")
        _overlay_parts.append(
            f"drawtext="
            f"text='{_safe}':"
            f"fontcolor=white:"
            f"fontsize=52:"
            f"font=Arial:"
            f"x=(w-text_w)/2:"
            f"y=(h-text_h)/2:"
            f"shadowcolor=black:"
            f"shadowx=2:"
            f"shadowy=2:"
            f"alpha='if(lt(t,0.5),t/0.5,if(gt(t,{_fade_out_start:.1f}),({duration:.1f}-t)/0.5,1))'"
        )
        _overlay_parts.append(
            f"drawtext="
            f"text='#{scene_index + 1}':"
            f"fontcolor=#888888:"
            f"fontsize=24:"
            f"x=(w-text_w)/2:"
            f"y=h/2+60"
        )

    _overlay_str = ",".join(_overlay_parts)

    if is_image(media_path):
        vf = (
            f"{_ken_burns_filter(width, height, duration, motion, zoom_max=zoom_max)},"
            f"{grade},"
            f"{_overlay_str},"
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

        # Verifica se o vídeo precisa de pre-upscale antes do motion filter
        # Vídeos do Replicate chegam em 1024x576 — precisam ser escalados
        # para pelo menos o target antes das expressões de crop dinâmico
        _source_needs_upscale = _video_needs_upscale(media_path, width, height)

        needs_loop = source_duration > 0 and source_duration < duration - 0.5

        base_vf = _video_motion_filter(width, height, duration, scene_index, motion)
        vf = f"{base_vf},{grade},{_overlay_str},{_fade_filter(duration, fade)}"
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
        print(f"❌ Erro renderizando cena ({media_path.name}):")
        if stderr:
            # Imprime as últimas 800 chars — onde o erro real aparece
            print(stderr[-800:])
        else:
            print(f"  código de saída: {error.returncode}")
        # Loga comando completo para debug
        safe_cmd = " ".join(str(c) for c in cmd)
        print(f"  CMD: {safe_cmd[:400]}")
        return False


def concat_scene_clips(
    clip_paths: list,
    output_path: Path,
    crossfade: float = 0.45,
    scene_types: list | None = None,
    platform: str = "youtube_dark",
    width: int = 1920,
    height: int = 1080,
) -> bool:
    """Concatena clips com crossfade suave entre cenas adjacentes."""
    from scripts.video.renderer import concat_video_clips

    if len(clip_paths) < 2 or crossfade <= 0.01:
        return concat_video_clips(clip_paths, output_path)

    durations = []
    for clip in clip_paths:
        d = probe_duration(clip)
        if d <= 0:
            d = 5.0  # fallback seguro
        durations.append(d)

    # Usa crossfade variável: mais longo em transições lentas, mais curto em rápidas
    if scene_types:
        fade_map = {"hook": 0.3, "contexto": 0.5, "encerramento": 0.6}
        crossfades = [fade_map.get(t, crossfade) for t in scene_types[:-1]]
    else:
        crossfades = [crossfade] * (len(clip_paths) - 1)

    if _concat_with_variable_crossfade(
        clip_paths, output_path, crossfades, durations, width, height,
    ):
        return True

    print("⚠️ Crossfade falhou, usando concat simples.")
    return concat_video_clips(clip_paths, output_path)


def _concat_with_crossfade(
    clip_paths: list,
    output_path: Path,
    crossfade: float,
    durations: list,
    width: int,
    height: int,
) -> bool:
    inputs = []
    for clip in clip_paths:
        inputs.extend(["-i", str(clip.resolve())])

    filter_parts = _normalize_input_filters(len(clip_paths), width, height)
    offset = durations[0] - crossfade

    if len(clip_paths) == 2:
        filter_parts.append(
            f"[n00][n01]xfade=transition=fade:duration={crossfade}:offset={offset:.3f}[vout]"
        )
    else:
        filter_parts.append(
            f"[n00][n01]xfade=transition=fade:duration={crossfade}:offset={offset:.3f}[v01]"
        )

        accumulated = durations[0] + durations[1] - crossfade
        for index in range(2, len(clip_paths)):
            prev = f"v{index - 1:02d}"
            next_label = f"v{index:02d}" if index < len(clip_paths) - 1 else "vout"
            offset = accumulated - crossfade
            filter_parts.append(
                f"[{prev}][n{index:02d}]xfade=transition=fade:duration="
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

    if not _run_ffmpeg(cmd, context="crossfade", output_path=output_path):
        print("⚠️ Crossfade falhou, usando concat simples.")
        return False
    return True


def _concat_with_variable_crossfade(
    clip_paths: list,
    output_path: Path,
    crossfades: list,
    durations: list,
    width: int,
    height: int,
) -> bool:
    """Crossfade com duração variável entre cenas adjacentes."""

    if len(clip_paths) < 2:
        return False

    inputs = []
    for clip in clip_paths:
        inputs.extend(["-i", str(clip.resolve())])

    filter_parts = _normalize_input_filters(len(clip_paths), width, height)
    cf = crossfades[0] if crossfades else 0.4
    offset = durations[0] - cf
    filter_parts.append(
        f"[n00][n01]xfade=transition=fade:duration={cf:.3f}:offset={offset:.3f}[v01]"
    )

    accumulated = durations[0] + durations[1] - cf
    for index in range(2, len(clip_paths)):
        prev = f"v{index - 1:02d}"
        next_label = f"v{index:02d}" if index < len(clip_paths) - 1 else "vout"
        cf = crossfades[index - 1] if index - 1 < len(crossfades) else 0.4
        offset = accumulated - cf
        filter_parts.append(
            f"[{prev}][n{index:02d}]xfade=transition=fade:duration="
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

    return _run_ffmpeg(cmd, context="crossfade variável", output_path=output_path)


def _trim_video_duration(
    input_path: Path,
    output_path: Path,
    duration: float,
) -> bool:
    """Recorta trilho de vídeo para duração exata (corrige drift de xfade/fps)."""

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path.resolve()),
        "-t", f"{duration:.3f}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "21",
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_path),
    ]
    return _run_ffmpeg(cmd, context="trim duração", output_path=output_path)


def render_scenes_video(
    result: dict,
    width: int,
    height: int,
    output_path: Path,
    assets_root: Path | None = None,
) -> Path | None:
    """Pipeline scene-aware com intro/outro de marca e motion por tipo de cena."""

    from scripts.video.renderer import _resolve_folder

    folder = _resolve_folder(result)
    platform = result.get("platform", "youtube_dark")
    config = get_brand_config(platform)
    kit = config.kit
    scenes = extract_scenes(result.get("cenas", {}))
    cenas_meta = result.get("cenas", {}) if isinstance(result.get("cenas"), dict) else {}
    synced = bool(cenas_meta.get("synced"))
    lofi_template = cenas_meta.get("roteiro_template") == "lofi_dark"

    if not scenes:
        return None

    if assets_root is None:
        assets_root = folder / "assets"
    else:
        assets_root = Path(assets_root)

    temp_dir = folder / "assets" / "scene_clips"
    temp_dir.mkdir(parents=True, exist_ok=True)

    clip_paths = []
    scene_types = []
    scene_count = len(scenes)
    media_scene_count = cenas_meta.get("media_scene_count") or scene_count
    topic = result.get("produto", {}).get("nome", "")

    if should_show_intro(platform) and not lofi_template:
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

    rendered_scenes = 0

    for i, scene in enumerate(scenes):
        duration = _scene_duration(scene, synced)

        media_idx = scene.get("media_index", i)
        media = resolve_scene_media(assets_root, media_idx, media_scene_count)
        scene_type = scene.get("tipo", "")
        scene_label = scene.get("visual", "")[:50]

        if not media:
            raise RenderSyncError(
                f"Sem mídia para cena {i + 1} ({scene_type}) — cobertura 100% obrigatória"
            )

        clip_out = temp_dir / f"scene_{i + 1:02d}.mp4"
        render_duration = duration

        if render_scene_clip(
            media, render_duration, clip_out, width, height,
            scene_index=i,
            platform=platform,
            scene_type=scene_type,
            scene_label=scene_label,
            scene=scene,
        ):
            clip_paths.append(clip_out)
            scene_types.append(scene_type)
            rendered_scenes += 1
            print(f"🎬 Cena {i + 1}/{scene_count} [{scene_type}]: {duration:.1f}s ({media.name})")
        else:
            raise RenderSyncError(f"Falha ao renderizar cena {i + 1} ({scene_type})")

    _validate_scene_coverage(scenes, rendered_scenes)

    if should_show_outro(platform) and not lofi_template:
        outro_card = temp_dir / "outro_card.jpg"
        outro_clip = temp_dir / "outro.mp4"
        if kit.render_outro_card(outro_card, topic=topic):
            # Outro é o último clip — sem transição xfade depois dele,
            # portanto não recebe compensação de crossfade.
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

    if not concat_scene_clips(
        clip_paths,
        video_only,
        platform=platform,
        width=width,
        height=height,
    ):
        return None

    narration_duration = float(cenas_meta.get("audio_duration") or 0)
    expected = compute_expected_video_duration(
        platform,
        scenes,
        synced=synced,
        narration_duration=narration_duration if narration_duration > 0 else None,
    )
    actual = probe_duration(video_only)
    if expected > 0 and abs(actual - expected) > 0.05:
        trimmed = temp_dir / "video_track_trimmed.mp4"
        if _trim_video_duration(video_only, trimmed, expected):
            video_only = trimmed

    # Libera espaço: remove clips intermediários após concatenação
    try:
        for clip in clip_paths:
            if clip.exists() and clip != video_only:
                clip.unlink()
    except Exception:
        pass

    return video_only


def mux_video_audio_subtitles(
    video_path: Path,
    audio_path: Path | None,
    subtitle_path: Path | None,
    output_path: Path,
    width: int,
    height: int,
    platform: str = "youtube_dark",
    soundtrack_path: Path | None = None,
) -> bool:
    """Combina vídeo, áudio, trilha sonora (com ducking) e legendas."""

    render_style = get_render_style(platform)
    opening = render_style.opening_fade_seconds
    video_filter = _scale_pad_filter(width, height)

    if subtitle_path and subtitle_path.exists():
        sub_filter = get_subtitle_ffmpeg_filter(subtitle_path, platform)
        if sub_filter:
            video_filter += f",{sub_filter}"

    watermark = watermark_filter_for_platform(platform)
    if watermark:
        video_filter += f",{watermark}"

    if render_style.film_grain:
        video_filter += f",{render_style.film_grain}"

    video_filter += f",fade=t=in:st=0:d={opening}"

    audio_duration = 0.0
    video_duration = probe_duration(video_path)

    if audio_path and audio_path.exists():
        audio_duration = probe_duration(audio_path)

    has_audio = audio_path and audio_path.exists() and audio_path.stat().st_size > 0
    has_soundtrack = soundtrack_path and soundtrack_path.exists() and soundtrack_path.stat().st_size > 0
    audio_delay = _audio_delay(platform) if has_audio else 0.0
    outro_seconds = (
        render_style.outro_seconds if should_show_outro(platform) else 0.0
    )
    closing = render_style.closing_fade_seconds
    fade_start = 0.0

    if has_audio and audio_duration > 0:
        target_duration = audio_delay + audio_duration + outro_seconds
        if video_duration > target_duration + 0.05:
            target_duration = video_duration
    else:
        target_duration = video_duration

    if video_duration > 0 and target_duration > video_duration + 0.05:
        pad_seconds = target_duration - video_duration
        video_filter += f",tpad=stop_mode=clone:stop_duration={pad_seconds:.3f}"

    if target_duration > closing + 1:
        fade_start = max(0.0, target_duration - closing)
        video_filter += f",fade=t=out:st={fade_start:.2f}:d={closing}"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
    ]

    input_index = 1
    narration_index = None
    soundtrack_index = None

    if has_audio:
        if audio_delay > 0:
            cmd.extend(["-itsoffset", f"{audio_delay:.3f}"])
        cmd.extend(["-i", str(audio_path.resolve())])
        narration_index = input_index
        input_index += 1

    if has_soundtrack:
        cmd.extend(["-stream_loop", "-1", "-i", str(soundtrack_path.resolve())])
        soundtrack_index = input_index
        input_index += 1

    cmd.extend([
        "-vf", video_filter,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
    ])

    if has_audio and has_soundtrack:
        af = (
            f"[{soundtrack_index}:a]volume=0.18,afade=t=in:st=0:d={opening},"
            f"afade=t=out:st={max(0.0, target_duration - closing):.2f}:d={closing}[bgm];"
            f"[{narration_index}:a]afade=t=in:st=0:d={opening},"
            f"afade=t=out:st={max(0.0, audio_duration - closing):.2f}:d={closing}[voice];"
            f"[bgm][voice]amix=inputs=2:duration=first:dropout_transition=2:weights=0.35 1.0[aout]"
        )
        cmd.extend([
            "-filter_complex", af,
            "-map", "0:v:0",
            "-map", "[aout]",
            "-c:a", "aac",
            "-b:a", "192k",
        ])
    elif has_audio:
        af = f"afade=t=in:st=0:d={opening}"
        if audio_duration > closing + 1:
            af += f",afade=t=out:st={audio_duration - closing:.2f}:d={closing}"
        cmd.extend([
            "-af", af,
            "-c:a", "aac",
            "-b:a", "192k",
            "-map", "0:v:0",
            "-map", f"{narration_index}:a:0",
        ])
    elif has_soundtrack:
        af = (
            f"volume=0.25,afade=t=in:st=0:d={opening},"
            f"afade=t=out:st={max(0.0, target_duration - closing):.2f}:d={closing}"
        )
        cmd.extend([
            "-af", af,
            "-c:a", "aac",
            "-b:a", "128k",
            "-map", "0:v:0",
            "-map", f"{soundtrack_index}:a:0",
        ])
    else:
        cmd.append("-an")

    if target_duration > 0 and (has_audio or has_soundtrack):
        cmd.extend(["-t", f"{target_duration:.3f}"])

    cmd.extend([
        "-movflags", "+faststart",
        str(output_path),
    ])

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        if not output_path.exists():
            return False

        if has_audio:
            validate_av_sync(
                output_path,
                audio_path,
                audio_offset=audio_delay,
                outro_seconds=outro_seconds,
            )

        return True

    except RenderSyncError:
        raise
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode("utf-8", errors="replace") if error.stderr else ""
        print(f"❌ Erro no mux final:")
        print(stderr if stderr.strip() else f"  código de saída: {error.returncode}")
        return False


def _audio_delay(platform: str) -> float:
    """Atraso do áudio para alinhar narração com cenas após intro visual."""

    if not should_show_intro(platform):
        return 0.0

    return get_render_style(platform).intro_seconds
