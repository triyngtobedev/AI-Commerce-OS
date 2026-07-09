import subprocess
from pathlib import Path



def render_video_project(result):

    product = result["produto"]["nome"]


    folder = (
        Path("output")
        / product.lower().replace(" ", "-")
    )



    videos_folder = (
        folder
        / "assets"
        / "videos"
    )


    images_folder = (
        folder
        / "assets"
        / "images"
    )



    audio_file = Path(
        result.get("audio", "")
    )


    subtitle_file = Path(
        result.get("subtitle_file", "")
    )



    media_files = []



    # =========================
    # BUSCAR VÍDEOS
    # =========================

    if videos_folder.exists():

        for ext in (
            "*.mp4",
            "*.mov"
        ):

            media_files.extend(
                videos_folder.glob(ext)
            )



    # =========================
    # FALLBACK IMAGENS
    # =========================

    if not media_files and images_folder.exists():

        for ext in (
            "*.jpg",
            "*.jpeg",
            "*.png"
        ):

            media_files.extend(
                images_folder.glob(ext)
            )



    media_files = sorted(
        media_files
    )



    if not media_files:

        print(
            "❌ Nenhuma mídia encontrada."
        )

        return None



    # =========================
    # CRIAR LISTA FFMPEG
    # =========================

    list_file = (
        folder
        /
        "ffmpeg_input.txt"
    )



    with open(
        list_file,
        "w",
        encoding="utf-8"
    ) as f:


        for media in media_files:


            path = (
                str(media.resolve())
                .replace("\\", "/")
            )


            f.write(
                f"file '{path}'\n"
            )



            if media.suffix.lower() in [
                ".jpg",
                ".jpeg",
                ".png"
            ]:

                f.write(
                    "duration 3\n"
                )



        if media_files[-1].suffix.lower() in [
            ".jpg",
            ".jpeg",
            ".png"
        ]:


            last = (
                str(
                    media_files[-1]
                    .resolve()
                )
                .replace("\\", "/")
            )


            f.write(
                f"file '{last}'\n"
            )



    output = (
        folder
        /
        "video_final.mp4"
    )



    # =========================
    # FILTRO BASE
    # =========================

    video_filter = (

        "scale=1080:1920:"
        "force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2"

    )



    # =========================
    # LEGENDAS
    # =========================

    if (
        subtitle_file.exists()
        and subtitle_file.stat().st_size > 0
    ):


        subtitle_path = (
            str(
                subtitle_file.resolve()
            )
            .replace(
                "\\",
                "/"
            )
            .replace(
                ":",
                "\\:"
            )
            .replace(
                "'",
                "\\'"
            )
        )



        video_filter += (
            f",subtitles='{subtitle_path}'"
        )



        print(
            "📝 Legenda aplicada."
        )


    else:

        print(
            "⚠️ Legenda ignorada."
        )



    # =========================
    # COMANDO FFMPEG
    # =========================

    cmd = [

        "ffmpeg",

        "-y",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        str(list_file)

    ]



    # =========================
    # AUDIO
    # =========================

    has_audio = (

        audio_file.exists()

        and

        audio_file.stat().st_size > 0

    )



    if has_audio:


        cmd.extend(
            [

                "-i",

                str(
                    audio_file.resolve()
                )

            ]
        )


        print(
            "🎙️ Áudio aplicado."
        )


    else:


        print(
            "⚠️ Sem áudio."
        )



    cmd.extend(
        [

            "-vf",

            video_filter,

            "-pix_fmt",

            "yuv420p",

            "-c:v",

            "libx264",

            "-preset",

            "veryfast",

            "-crf",

            "23"

        ]
    )



    if has_audio:


        cmd.extend(
            [

                "-c:a",

                "aac",

                "-b:a",

                "192k"

            ]
        )



    cmd.extend(
        [

            "-shortest",

            "-t",

            "30",

            "-movflags",

            "+faststart",

            str(output)

        ]
    )



    print(
        "\n🎬 Renderizando vídeo..."
    )



    subprocess.run(
        cmd,
        check=True
    )



    print(
        f"🎬 Vídeo final criado: {output}"
    )



    return output