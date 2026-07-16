from pathlib import Path
import requests

from scripts.utils.slug import content_output_dir


def _output_folder(subject):
    platform = subject.get("_output_platform")
    return content_output_dir(subject, platform=platform)


def download_file(url, path):

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    path.write_bytes(
        response.content
    )


def select_video_file(video):

    files = video.get(
        "video_files",
        []
    )

    if not files:
        return None

    for file in files:
        if file.get("quality") == "hd":
            return file.get("link")

    for file in files:
        if file.get("quality") == "sd":
            return file.get("link")

    return files[0].get("link")


def download_images(product, media_data):

    folder = (
        _output_folder(product)
        / "assets"
    )

    videos_folder = folder / "videos"
    images_folder = folder / "images"

    videos_folder.mkdir(parents=True, exist_ok=True)
    images_folder.mkdir(parents=True, exist_ok=True)

    video_count = 1
    image_count = 1
    used_pexels_ids = set()

    for item in media_data.get("assets", []):

        resultado = item.get("resultado", {})

        for video in resultado.get("videos", [])[:2]:

            pexels_id = video.get("id")

            if pexels_id and pexels_id in used_pexels_ids:
                continue

            url = select_video_file(video)

            if not url:
                continue

            try:
                file = videos_folder / f"video-{video_count}.mp4"

                download_file(url, file)

                print(f"🎬 Vídeo salvo: {file}")

                if pexels_id:
                    used_pexels_ids.add(pexels_id)

                video_count += 1

            except Exception as error:
                print(f"Erro baixando vídeo: {error}")

        for photo in resultado.get("photos", [])[:1]:

            pexels_id = photo.get("id")

            if pexels_id and pexels_id in used_pexels_ids:
                continue

            url = photo.get("src", {}).get("original")

            if not url:
                continue

            try:
                file = images_folder / f"imagem-{image_count}.jpg"

                download_file(url, file)

                print(f"🖼️ Imagem salva: {file}")

                if pexels_id:
                    used_pexels_ids.add(pexels_id)

                image_count += 1

            except Exception as error:
                print(f"Erro baixando imagem: {error}")

    return folder


def download_videos(product, media_data):

    return download_images(
        product,
        media_data
    )
