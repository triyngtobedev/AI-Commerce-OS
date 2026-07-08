from pathlib import Path
import requests


def download_images(product, media_data):

    folder = (
        Path("output")
        / product["nome"].lower().replace(" ", "-")
        / "assets"
        / "images"
    )

    folder.mkdir(
        parents=True,
        exist_ok=True
    )


    count = 1


    for item in media_data["assets"]:

        resultado = item["resultado"]

        photos = resultado.get(
            "photos",
            []
        )


        for photo in photos[:3]:

            url = photo["src"]["original"]

            response = requests.get(
                url
            )

            file = folder / f"imagem-{count}.jpg"

            file.write_bytes(
                response.content
            )

            count += 1


    return folder