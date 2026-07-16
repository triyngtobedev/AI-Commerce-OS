from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from scripts.video.pexels_provider import search_pexels
from scripts.video.pixabay_provider import search_pixabay
from scripts.video.wikimedia_provider import search_wikimedia
from scripts.utils.slug import product_output_dir, content_output_dir
from scripts.core.production.logger import get_logger


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


def _search_pexels_only(busca: str) -> dict:
    # TikTok e demais formatos verticais: prioriza retrato + Full HD vertical.
    return search_pexels(
        busca,
        orientation="portrait",
        min_width=1080,
        min_height=1920,
    )


def _search_youtube_dark_chain(busca: str) -> dict:
    """Wikimedia → Pixabay → Pexels até encontrar mídia."""

    for provider_name, search_fn in (
        ("wikimedia", search_wikimedia),
        ("pixabay", search_pixabay),
        ("pexels", search_pexels),
    ):
        media = search_fn(busca)
        if _has_media(media):
            media = dict(media)
            media["provedor"] = provider_name
            return media

    return {"videos": [], "photos": [], "provedor": "none"}


def _search_for_platform(platform: str, busca: str) -> dict:
    if platform == "youtube_dark":
        return _search_youtube_dark_chain(busca)
    return _search_pexels_only(busca)


def _process_query(platform: str, query: dict) -> dict:
    """Processa uma query de mídia (paralelizável)."""

    busca = query["busca"]
    used_query = busca

    media = _search_for_platform(platform, busca)

    if not _has_media(media) and query.get("busca_fallback"):
        fallback = query["busca_fallback"]
        get_logger("media_search").warning(
            f"Sem resultados para '{busca}'. Fallback: '{fallback}'"
        )
        media = _search_for_platform(platform, fallback)
        used_query = fallback

    provedor = media.get("provedor", "pexels" if platform != "youtube_dark" else "none")

    return {
        "query": used_query,
        "query_original": busca,
        "provedor": provedor,
        "resultado": media,
    }


def search_media(product, queries, *, max_workers: int = 4):

    folder = (
        _output_folder(product)
        / "assets"
    )

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    platform = product.get("_output_platform", "")
    results = [None] * len(queries)

    logger = get_logger("media_search")
    logger.info(f"Buscando mídia para {len(queries)} queries (workers={max_workers})")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(_process_query, platform, query): idx
            for idx, query in enumerate(queries)
        }

        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                logger.error(f"Query {idx} falhou", error=str(exc))
                results[idx] = {
                    "query": queries[idx].get("busca", ""),
                    "query_original": queries[idx].get("busca", ""),
                    "provedor": "none",
                    "resultado": {"videos": [], "photos": []},
                }

    results = [r for r in results if r is not None]

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
