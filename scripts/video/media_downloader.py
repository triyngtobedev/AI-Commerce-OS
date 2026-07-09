from pathlib import Path
import requests



def slugify(text):

    return (
        text
        .lower()
        .replace(" ", "-")
        .replace("/", "-")
    )



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
        Path("output")
        / slugify(product["nome"])
        / "assets"
    )


    videos_folder = folder / "videos"
    images_folder = folder / "images"


    videos_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    images_folder.mkdir(
        parents=True,
        exist_ok=True
    )


    video_count = 1
    image_count = 1


    for item in media_data.get("assets", []):

        resultado = item.get(
            "resultado",
            {}
        )


        # ----------------------
        # Vídeos
        # ----------------------

        for video in resultado.get("videos", [])[:2]:

            url = select_video_file(video)

            if not url:
                continue


            try:

                file = (
                    videos_folder /
                    f"video-{video_count}.mp4"
                )

                download_file(
                    url,
                    file
                )

                print(
                    f"🎬 Vídeo salvo: {file}"
                )

                video_count += 1


            except Exception as error:

                print(
                    f"Erro baixando vídeo: {error}"
                )



        # ----------------------
        # Imagens fallback
        # ----------------------

        for photo in resultado.get("photos", [])[:3]:

            url = (
                photo
                .get("src", {})
                .get("original")
            )


            if not url:
                continue


            try:

                file = (
                    images_folder /
                    f"imagem-{image_count}.jpg"
                )


                download_file(
                    url,
                    file
                )


                print(
                    f"🖼️ Imagem salva: {file}"
                )


                image_count += 1


            except Exception as error:

                print(
                    f"Erro baixando imagem: {error}"
                )


    return folder



# Compatibilidade com versões novas do pipeline

def download_videos(product, media_data):

    return download_images(
        product,
        media_data
    )