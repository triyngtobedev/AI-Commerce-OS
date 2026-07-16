from pathlib import Path

from scripts.utils.slug import product_output_dir, content_output_dir


def _assets_dir(subject):
    """Resolve diretório de assets considerando plataforma."""

    platform = subject.get("_output_platform")

    return content_output_dir(
        subject,
        platform=platform,
    ) / "assets"


def prepare_assets(product):

    folder = _assets_dir(product)

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


def clear_media_assets(product):
    """
    Remove vídeos e imagens antigos antes de nova busca.
    Evita acúmulo de mídia em reprocessamentos.
    """

    assets = _assets_dir(product)

    for subfolder in ("videos", "images"):

        folder = assets / subfolder

        if not folder.exists():
            continue

        for old_file in folder.glob("*"):

            try:
                old_file.unlink()
            except Exception as error:
                print(
                    f"⚠️ Não foi possível remover {old_file}: {error}"
                )