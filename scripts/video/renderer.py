import subprocess
from pathlib import Path


def render_video_project(result):

    product = result["produto"]["nome"]

    folder = (
        Path("output")
        / product.lower().replace(" ", "-")
    )

    images = folder / "assets" / "images"

    files = []

    for ext in ("*.jpg", "*.jpeg", "*.png"):
        files.extend(images.glob(ext))

    files = sorted(files)

    if not files:
        print("Nenhuma imagem encontrada.")
        return None


    scenes = result.get(
        "cenas",
        {}
    )

    scene_list = scenes.get(
        "cenas",
        []
    )


    list_file = folder / "ffmpeg_input.txt"


    with open(
        list_file,
        "w",
        encoding="utf-8"
    ) as f:

        for image in files:

            f.write(
                f"file '{image.resolve()}'\n"
            )

            f.write(
                "duration 3\n"
            )


        f.write(
            f"file '{files[-1].resolve()}'\n"
        )


    output = folder / "video_final.mp4"


    text = (
        scene_list[0]["narracao"]
        if scene_list
        else product
    )


    text = (
        text
        .replace("'", "")
        .replace(":", "")
    )


    video_filter = (
        "scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
        "zoompan="
        "z='min(zoom+0.0015,1.15)':"
        "d=90:"
        "s=1080x1920:"
        "fps=30,"
        f"drawtext=text='{text}':"
        "fontcolor=white:"
        "fontsize=55:"
        "x=(w-text_w)/2:"
        "y=h-250"
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