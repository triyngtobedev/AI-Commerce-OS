import json
from pathlib import Path

from scripts.utils.slug import slugify, content_output_dir
from scripts.core.platform_config import get_platform, TIKTOK_SHOP


def _resolve_folder(result):

    product = result.get("produto", {})
    platform_id = result.get("platform")
    platform = product.get("_output_platform") or platform_id

    return content_output_dir(
        product,
        platform=platform if platform else None,
    )


def build_video_project(result):

    product = (
        result
        .get("produto", {})
        .get(
            "nome",
            "produto"
        )
    )

    folder = _resolve_folder(result)


    folder.mkdir(
        parents=True,
        exist_ok=True
    )



    conteudo = result.get("conteudo", {})
    cenas_data = result.get("cenas", {})

    duracao_segundos = None

    if isinstance(cenas_data, dict):
        duracao_segundos = cenas_data.get("audio_duration")

    narracao_meta = conteudo.get("narracao_meta", {})

    if not duracao_segundos:
        duracao_segundos = narracao_meta.get("duracao_estimada_segundos")

    project = {
        "produto": product,
        "duracao_segundos": duracao_segundos,
        "duracao": conteudo.get("duracao", "8 minutos"),
        "cenas": cenas_data,
        "narracao": conteudo.get("texto_narracao", ""),
        "legenda": result.get("legenda", {}),
        "audio": result.get("audio"),
        "subtitle_file": result.get("subtitle_file"),
        "status": "READY_FOR_RENDER",
        "render_mode": (
            "scene_aware"
            if isinstance(cenas_data, dict) and cenas_data.get("synced")
            else "legacy_concat"
        ),
    }



    file = (
        folder
        /
        "video_project.json"
    )



    with open(
        file,
        "w",
        encoding="utf-8"
    ) as f:


        json.dump(
            project,
            f,
            ensure_ascii=False,
            indent=4
        )



    return project