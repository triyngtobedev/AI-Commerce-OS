from pathlib import Path


def prepare_assets(product):

    folder = (
        Path("output") /
        product["nome"].lower().replace(" ", "-") /
        "assets"
    )

    folder.mkdir(
        parents=True,
        exist_ok=True
    )


    folders = [
        "images",
        "videos",
        "audio"
    ]


    for item in folders:

        (folder / item).mkdir(
            exist_ok=True
        )


    return folder