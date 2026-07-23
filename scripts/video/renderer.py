import subprocess
import json
import shutil
import time

from pathlib import Path

from scripts.utils.slug import slugify, content_output_dir
from scripts.core.platform_config import get_platform, TIKTOK_SHOP
from scripts.video.scene_renderer import (
    render_scenes_video,
    mux_video_audio_subtitles,
    RenderSyncError,
)
from scripts.video.subtitle_generator import get_subtitle_ffmpeg_filter
from scripts.core.emotional_timeline import EmotionalTimeline


def _run_ffmpeg(cmd: list, *, context: str = "") -> None:
    """Executa FFmpeg e imprime stderr completo nos logs em caso de falha."""

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode("utf-8", errors="replace") if error.stderr else ""
        label = f" ({context})" if context else ""
        print(f"❌ FFmpeg falhou{label}:")
        if stderr.strip():
            print(stderr)
        else:
            print(f"  código de saída: {error.returncode}")
        raise


def _resolve_folder(result):

    product = result.get("produto", {})
    platform_id = result.get("platform")

    if isinstance(product, str):
        product = {
            "nome": product,
            "_output_platform": platform_id,
        }

    platform = product.get("_output_platform") or platform_id

    return content_output_dir(
        product,
        platform=platform if platform else None,
    )


def _resolve_render_dimensions(result):

    platform_id = result.get("platform")

    if platform_id:

        try:

            config = get_platform(platform_id)

            return (
                config.render.width,
                config.render.height,
            )

        except ValueError:

            pass

    return (
        TIKTOK_SHOP.render.width,
        TIKTOK_SHOP.render.height,
    )


def _has_synced_scenes(result) -> bool:
    """Verifica se cenas possuem duração sincronizada com áudio."""

    cenas = result.get("cenas", {})

    if isinstance(cenas, dict):
        scenes = cenas.get("cenas", [])
        return bool(cenas.get("synced")) and bool(scenes)

    return False


def _should_use_scene_renderer(result) -> bool:
    """YouTube Dark com cenas sincronizadas usa render scene-aware."""

    platform = result.get("platform", "")

    if platform == "youtube_dark" and _has_synced_scenes(result):
        return True

    return False


def update_project_status(
    folder,
    video_path
):

    project_file = (
        folder
        /
        "video_project.json"
    )


    if not project_file.exists():

        return



    with open(
        project_file,
        "r",
        encoding="utf-8"
    ) as file:

        project = json.load(
            file
        )



    project["status"] = (
        "RENDER_COMPLETED"
    )


    project["video"] = (
        str(video_path)
    )



    with open(
        project_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            project,
            file,
            ensure_ascii=False,
            indent=4
        )



def concat_video_clips(clip_paths: list, output_path: Path) -> bool:
    """
    Concatena clips de vídeo via FFmpeg demuxer (-f concat).

    Usa apenas scene_*.mp4 encontrados no diretório de saída —
    ignora clip_paths (que pode conter intro.mp4/outro.mp4 não gerados).
    Tenta stream copy (-c copy) primeiro; se falhar, re-encoda com libx264.
    """
    clips_dir = output_path.parent
    clips_dir.mkdir(parents=True, exist_ok=True)

    paths = sorted(clips_dir.glob("scene_*.mp4"))
    if not paths:
        return False

    if len(paths) == 1:
        shutil.copy2(paths[0], output_path)
        return output_path.exists()

    list_file = clips_dir / "concat_list.txt"
    with open(list_file, "w", encoding="utf-8") as file:
        for clip in paths:
            path = str(clip.resolve()).replace("\\", "/")
            file.write(f"file '{path}'\n")

    base_cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
    ]

    copy_cmd = [*base_cmd, "-c", "copy", str(output_path)]
    try:
        subprocess.run(copy_cmd, check=True, capture_output=True)
        if output_path.exists():
            return True
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode("utf-8", errors="replace") if error.stderr else ""
        print("⚠️ Concat -c copy falhou, re-encoding com libx264...")
        if stderr.strip():
            print(stderr[-500:])

    reencode_cmd = [
        *base_cmd,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "21",
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_path),
    ]
    try:
        subprocess.run(reencode_cmd, check=True, capture_output=True)
        return output_path.exists()
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode("utf-8", errors="replace") if error.stderr else ""
        print("❌ FFmpeg concat falhou:")
        if stderr.strip():
            print(stderr[-800:])
        else:
            print(f"  código de saída: {error.returncode}")
        return False


def _render_legacy_concat(result, folder, width, height, output):
    """Renderização legada para TikTok Shop e fallback."""

    videos_folder = folder / "assets" / "videos"
    images_folder = folder / "assets" / "images"

    media_files = []

    if videos_folder.exists():
        media_files.extend(videos_folder.glob("*.mp4"))
        media_files.extend(videos_folder.glob("*.mov"))

    if not media_files and images_folder.exists():
        media_files.extend(images_folder.glob("*.jpg"))
        media_files.extend(images_folder.glob("*.jpeg"))
        media_files.extend(images_folder.glob("*.png"))

    media_files = sorted(media_files)

    if not media_files:
        print("❌ Nenhuma mídia encontrada.")
        return None

    list_file = folder / "ffmpeg_input.txt"

    with open(list_file, "w", encoding="utf-8") as file:
        for media in media_files:
            path = str(media.resolve()).replace("\\", "/")
            file.write(f"file '{path}'\n")

            if media.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                file.write("duration 3\n")

        last = media_files[-1]

        if last.suffix.lower() in [".jpg", ".jpeg", ".png"]:
            path = str(last.resolve()).replace("\\", "/")
            file.write(f"file '{path}'\n")

    video_filter = (
        f"scale={width}:{height}:"
        "force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
    )

    subtitle_file = result.get("subtitle_file")
    platform = result.get("platform", "youtube_dark")

    if subtitle_file:
        subtitle = Path(subtitle_file)
        if subtitle.exists():
            sub_filter = get_subtitle_ffmpeg_filter(subtitle, platform)
            if sub_filter:
                video_filter += f",{sub_filter}"
                print("📝 Legenda aplicada.")

    audio_file = result.get("audio")
    has_audio = False
    audio = None

    if audio_file:
        audio = Path(audio_file)
        has_audio = audio.exists() and audio.stat().st_size > 0

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
    ]

    if has_audio:
        cmd.extend(["-i", str(audio.resolve())])
        print("🎙️ Áudio aplicado.")

    cmd.extend([
        "-vf", video_filter,
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
    ])

    if has_audio:
        cmd.extend(["-c:a", "aac", "-b:a", "192k"])

    cmd.extend(["-shortest", "-movflags", "+faststart", str(output)])

    _run_ffmpeg(cmd, context="concat legado")
    return output


def _render_scene_aware(result, folder, width, height, output):
    """Renderização scene-aware para YouTube Dark."""

    print("🎬 Modo scene-aware (duração sincronizada + transições)")

    video_track = render_scenes_video(result, width, height, output, assets_root=folder / "assets")

    if not video_track:
        print("⚠️ Scene renderer falhou — fallback para concat legado")
        return _render_legacy_concat(result, folder, width, height, output)

    audio_path = None
    if result.get("audio"):
        audio_path = Path(result["audio"])

    soundtrack_path = None
    soundtrack_ref = result.get("soundtrack")
    if soundtrack_ref:
        soundtrack_path = Path(soundtrack_ref)
    else:
        default_soundtrack = folder / "assets" / "audio" / "soundtrack.mp3"
        if default_soundtrack.exists():
            soundtrack_path = default_soundtrack

    subtitle_path = None
    if result.get("subtitle_file"):
        subtitle_path = Path(result["subtitle_file"])

    success = mux_video_audio_subtitles(
        video_track,
        audio_path,
        subtitle_path,
        output,
        width,
        height,
        platform=result.get("platform", "youtube_dark"),
        soundtrack_path=soundtrack_path,
    )

    if not success:
        return None

    return output


def render_video(
    timeline,
    scenes,
    audio,
    output_path=None,
    width=1920,
    height=1080,
    subtitles=None,
    platform="youtube_dark",
    produto=None,
):
    """
    Ponto de integração futuro para efeitos emocionais no render.

    Args:
        timeline: EmotionalTimeline ou dict — fonte única de emoções
        scenes: estrutura de cenas enriquecida
        audio: caminho do áudio de narração
        output_path: destino do vídeo final

    Pontos de integração futuros (por seção emocional):
        - zoom: hints["zoom_intensity"] por cena
        - shake: emotion == "impact" && intensity > 0.8
        - flash: transição rápida em "impact"
        - blur: emotion == "mystery" com transição lenta
        - silêncio: timeline.pause_before / pause_after
        - trilha sonora: mapear emotion → stem de áudio ambiente
    """

    if isinstance(timeline, dict):
        timeline = EmotionalTimeline.from_dict(timeline)

    produto_dict = dict(produto) if isinstance(produto, dict) else {}
    if platform and not produto_dict.get("_output_platform"):
        produto_dict["_output_platform"] = platform

    result = {
        "produto": produto_dict,
        "cenas": scenes if isinstance(scenes, dict) else {"cenas": scenes},
        "audio": str(audio) if audio else None,
        "platform": platform,
        "emotional_timeline": timeline.to_dict() if timeline else None,
    }

    if subtitles:
        result["subtitle_file"] = str(subtitles)

    folder = _resolve_folder(result)
    folder.mkdir(parents=True, exist_ok=True)
    output = Path(output_path) if output_path else folder / "video_final.mp4"
    assets_root = folder / "assets"

    video_track = render_scenes_video(
        result, width, height, output, assets_root=assets_root
    )

    if not video_track:
        return None

    audio_path = Path(audio) if audio else None
    subtitle_path = Path(subtitles) if subtitles else None

    soundtrack_path = None
    if result.get("soundtrack"):
        soundtrack_path = Path(result["soundtrack"])
    else:
        default_soundtrack = folder / "assets" / "audio" / "soundtrack.mp3"
        if default_soundtrack.exists():
            soundtrack_path = default_soundtrack

    success = mux_video_audio_subtitles(
        video_track,
        audio_path,
        subtitle_path,
        output,
        width,
        height,
        platform=platform,
        soundtrack_path=soundtrack_path,
    )

    return output if success else None


def render_video_project(result):

    product = (
        result
        .get("produto", {})
        .get("nome", "produto")
    )

    folder = _resolve_folder(result)
    folder.mkdir(parents=True, exist_ok=True)

    output = folder / "video_final.mp4"
    width, height = _resolve_render_dimensions(result)

    print("\n🎬 Renderizando vídeo...")

    try:
        if _should_use_scene_renderer(result):
            timeline_data = (
                result.get("emotional_timeline")
                or result.get("cenas", {}).get("emotional_timeline")
                or (result.get("roteiro", {}).get("_meta", {}) or {}).get("emotional_timeline")
            )
            if timeline_data:
                result_path = render_video(
                    timeline=timeline_data,
                    scenes=result.get("cenas", {}),
                    audio=result.get("audio"),
                    output_path=str(output),
                    width=width,
                    height=height,
                    subtitles=result.get("subtitle_file"),
                    platform=result.get("platform", "youtube_dark"),
                    produto=result.get("produto"),
                )
            else:
                result_path = _render_scene_aware(
                    result, folder, width, height, output
                )
        else:
            result_path = _render_legacy_concat(
                result, folder, width, height, output
            )

    except (subprocess.CalledProcessError, RenderSyncError) as error:
        print("❌ Erro no render:")
        print(error)
        return None

    if not result_path:
        print(
            "❌ Render abortado — vídeo final não gerado "
            "(sem mídia, FFmpeg falhou ou mux retornou falso; veja logs acima)."
        )
        return None

    if not output.exists():
        print(f"❌ Arquivo de saída ausente após render: {output}")
        return None

    time.sleep(1)

    update_project_status(folder, output)

    resolved = output.resolve()
    print(f"🎬 Vídeo final criado: {resolved}")
    print(f"PIPELINE_OUTPUT_VIDEO={resolved}")

    return output
