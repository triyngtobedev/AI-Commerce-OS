from pathlib import Path
import json

from scripts.video.pexels_provider import search_pexels
from scripts.utils.slug import product_output_dir, content_output_dir


def _output_folder(subject):
    """Resolve pasta de output considerando plataforma."""

    platform = subject.get("_output_platform")

    return content_output_dir(
        subject,
        platform=platform,
    )


def _has_media(media):

    return bool(
        media.get("videos")
        or media.get("photos")
    )


def search_media(product, queries):

    folder = (
        _output_folder(product)
        / "assets"
    )

    folder.mkdir(
        parents=True,
        exist_ok=True
    )


    results = []


    for query in queries:

        busca = query["busca"]
        used_query = busca

        media = search_pexels(
            busca
        )

        if (
            not _has_media(media)
            and query.get("busca_fallback")
        ):

            fallback = query["busca_fallback"]

            print(
                f"⚠️ Sem resultados para '{busca}'. "
                f"Tentando fallback: '{fallback}'"
            )

            media = search_pexels(
                fallback
            )

            used_query = fallback

        results.append(
            {
                "query": used_query,
                "query_original": busca,
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