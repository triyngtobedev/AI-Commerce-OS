from pathlib import Path
import requests

from scripts.utils.slug import content_output_dir

QUALITY_PRIORITY = {
    "uhd": 200,
    "4k": 200,
    "hd": 100,
    "sd": 50,
    "large": 90,
    "medium": 60,
    "small": 30,
    "tiny": 10,
}


def _output_folder(subject):
    platform = subject.get("_output_platform")
    return content_output_dir(subject, platform=platform)


def download_file(url, path, timeout=60):
    response = requests.get(
        url,
        timeout=timeout,
        stream=True,
    )

    response.raise_for_status()

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as handle:
        for chunk in response.iter_content(chunk_size=65536):
            if chunk:
                handle.write(chunk)


def select_video_file(video, min_width=1920, min_height=1080):
    """
    Seleciona melhor arquivo de vídeo disponível (prioriza 4K/1080p).
    Suporta qualidades Pexels (hd/sd) e Pixabay (large/medium/small/tiny).
    """

    files = video.get("video_files", [])

    if not files:
        return None

    def rank(file_info):
        quality = QUALITY_PRIORITY.get(file_info.get("quality", ""), 0)
        width = file_info.get("width", 0)
        height = file_info.get("height", 0)
        pixels = width * height
        meets_hd = width >= 1920 and height >= 1080
        meets_min = width >= min_width and height >= min_height
        tier = 3 if meets_hd else (2 if meets_min else 1)
        return (tier, pixels + quality)

    ranked = sorted(files, key=rank, reverse=True)

    for file_info in ranked:
        width = file_info.get("width", 0)
        height = file_info.get("height", 0)
        if width < min_width or height < min_height:
            continue
        link = file_info.get("link")
        if link:
            return link

    return None


def select_video_file_with_fallback(video):
    """Tenta 1080p+; aceita 720p apenas se não houver melhor opção."""

    url = select_video_file(video, min_width=1920, min_height=1080)
    if url:
        return url, 1920, 1080

    url = select_video_file(video, min_width=1280, min_height=720)
    if url:
        return url, 1280, 720

    return None, 0, 0


def select_photo_url(photo, min_width=1920):
    """Seleciona URL da maior foto disponível (prioriza original/large2x)."""

    src = photo.get("src", {})
    if not src:
        return None

    candidates = [
        ("original", src.get("original")),
        ("large2x", src.get("large2x")),
        ("large", src.get("large")),
        ("largeImageURL", src.get("largeImageURL")),
        ("medium", src.get("medium")),
        ("webformatURL", src.get("webformatURL")),
    ]

    for _, url in candidates:
        if url:
            return url

    return None


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

            url = select_photo_url(photo)

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
