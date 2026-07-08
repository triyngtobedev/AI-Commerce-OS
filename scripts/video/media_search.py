from pathlib import Path
import json

from scripts.video.pexels_provider import search_pexels


def search_media(product, queries):

    folder = (
        Path("output")
        / product["nome"].lower().replace(" ", "-")
        / "assets"
    )

    folder.mkdir(
        parents=True,
        exist_ok=True
    )


    results = []


    for query in queries:

        busca = query["busca"]

        media = search_pexels(
            busca
        )

        results.append(
            {
                "query": busca,
                "resultado": media
            }
        )


    output = {
        "produto": product["nome"],
        "assets": results
    }


    with open(
        folder / "media_search.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=4
        )


    return output