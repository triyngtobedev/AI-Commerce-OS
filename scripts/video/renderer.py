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


    media_files = []


    # PRIORIDADE: VÍDEOS
    if videos_folder.exists():

        for ext in ("*.mp4", "*.mov"):
            media_files.extend(
                videos_folder.glob(ext)
            )


    # FALLBACK: IMAGENS
    if not media_files and images_folder.exists():

        for ext in ("*.jpg", "*.jpeg", "*.png"):
            media_files.extend(
                images_folder.glob(ext)
            )


    media_files = sorted(media_files)


    if not media_files:
        print("Nenhuma mídia encontrada.")
        return None



    list_file = folder / "ffmpeg_input.txt"


    with open(
        list_file,
        "w",
        encoding="utf-8"
    ) as f:

        for media in media_files:

            f.write(
                f"file '{media.resolve()}'\n"
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
            f.write(
                f"file '{media_files[-1].resolve()}'\n"
            )



    output = folder / "video_final.mp4"



    video_filter = (
        "scale=1080:1920:"
        "force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
    )


    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-vf",
        video_filter,
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-movflags",
        "+faststart",
        str(output)
    ]


    subprocess.run(
        cmd,
        check=True
    )


    print(
        f"Vídeo criado: {output}"
    )


    return output