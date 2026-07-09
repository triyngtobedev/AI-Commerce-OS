import subprocess
import json
import time

from pathlib import Path



def slugify(text):

    return (
        str(text)
        .lower()
        .replace(" ", "-")
        .replace("/", "-")
        .replace("\\", "-")
    )



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



def render_video_project(result):


    product = (
        result
        .get("produto", {})
        .get(
            "nome",
            "produto"
        )
    )



    folder = (
        Path("output")
        /
        slugify(product)
    )



    folder.mkdir(
        parents=True,
        exist_ok=True
    )



    videos_folder = (
        folder
        /
        "assets"
        /
        "videos"
    )


    images_folder = (
        folder
        /
        "assets"
        /
        "images"
    )



    media_files = []



    if videos_folder.exists():

        media_files.extend(
            videos_folder.glob("*.mp4")
        )

        media_files.extend(
            videos_folder.glob("*.mov")
        )



    if not media_files and images_folder.exists():

        media_files.extend(
            images_folder.glob("*.jpg")
        )

        media_files.extend(
            images_folder.glob("*.jpeg")
        )

        media_files.extend(
            images_folder.glob("*.png")
        )



    media_files = sorted(
        media_files
    )



    if not media_files:

        print(
            "❌ Nenhuma mídia encontrada."
        )

        return None



    list_file = (
        folder
        /
        "ffmpeg_input.txt"
    )



    with open(
        list_file,
        "w",
        encoding="utf-8"
    ) as file:


        for media in media_files:

            path = (
                str(
                    media.resolve()
                )
                .replace(
                    "\\",
                    "/"
                )
            )


            file.write(
                f"file '{path}'\n"
            )



            if media.suffix.lower() in [
                ".jpg",
                ".jpeg",
                ".png"
            ]:

                file.write(
                    "duration 3\n"
                )



        last = media_files[-1]


        if last.suffix.lower() in [
            ".jpg",
            ".jpeg",
            ".png"
        ]:

            path = (
                str(
                    last.resolve()
                )
                .replace(
                    "\\",
                    "/"
                )
            )


            file.write(
                f"file '{path}'\n"
            )



    output = (
        folder
        /
        "video_final.mp4"
    )



    video_filter = (

        "scale=1080:1920:"
        "force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2"

    )



    subtitle_file = result.get(
        "subtitle_file"
    )



    if subtitle_file:

        subtitle = Path(
            subtitle_file
        )


        if subtitle.exists():

            subtitle_path = (
                subtitle
                .resolve()
                .as_posix()
                .replace(
                    ":",
                    "\\:"
                )
            )


            video_filter += (
                f",subtitles='{subtitle_path}'"
            )


            print(
                "📝 Legenda aplicada."
            )



    audio_file = result.get(
        "audio"
    )


    has_audio = False


    audio = None



    if audio_file:

        audio = Path(
            audio_file
        )


        has_audio = (
            audio.exists()
            and
            audio.stat().st_size > 0
        )



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



    if has_audio:

        cmd.extend(
            [
                "-i",
                str(
                    audio.resolve()
                )
            ]
        )


        print(
            "🎙️ Áudio aplicado."
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

            "-movflags",
            "+faststart",

            str(output)

        ]
    )



    print(
        "\n🎬 Renderizando vídeo..."
    )



    try:

        subprocess.run(
            cmd,
            check=True
        )


    except subprocess.CalledProcessError as error:

        print(
            "❌ Erro no FFmpeg:"
        )

        print(error)

        return None



    # Aguarda o Windows liberar o arquivo
    time.sleep(1)



    update_project_status(
        folder,
        output
    )



    print(
        f"🎬 Vídeo final criado: {output}"
    )



    return output