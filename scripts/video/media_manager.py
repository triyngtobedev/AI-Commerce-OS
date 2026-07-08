from pathlib import Path


def prepare_media_folder(product_name):
    """
    Cria estrutura de mídia do produto.
    """

    folder_name = (
        product_name.lower()
        .replace(" ", "-")
    )

    media_folder = (
        Path("output")
        / folder_name
        / "media"
    )

    media_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    return media_folder