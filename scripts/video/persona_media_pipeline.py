"""
Persona Media Pipeline
Pipeline alternativo ao Pexels.
Quando CONTENT_MODE=persona,
gera imagens utilizando a influenciadora virtual.
Mantém compatibilidade total com renderer.py,
pois salva no mesmo padrão:
output/{produto}/assets/images/imagem-N.png
"""

import os
from pathlib import Path

from scripts.persona.persona_generator import (
    generate_persona_reference
)
from scripts.persona.persona_scene_generator import (
    generate_persona_image
)


def slugify(text):
    """
    Cria nome de pasta compatível.
    """
    return (
        text.lower()
        .replace(" ", "-")
        .replace("/", "-")
    )


def get_images_folder(product):
    """
    Retorna pasta padrão do renderer.
    """
    folder = (
        Path("output")
        / slugify(product["nome"])
        / "assets"
        / "images"
    )
    folder.mkdir(
        parents=True,
        exist_ok=True
    )
    return folder


def clear_old_assets(images_folder):
    """
    Remove vídeos e imagens de execuções anteriores.

    Isso evita dois problemas silenciosos:

    1. Sobra de vídeos de um teste em modo stock anterior —
       o renderer.py prioriza vídeo sobre imagem, então se
       existir qualquer .mp4 na pasta de vídeos, ele ignora
       as imagens novas da persona sem avisar nada.

    2. Sobra de imagens de uma execução anterior da persona
       com mais cenas do que a atual (ex: rodou com 4 cenas,
       agora roda com 3 — sem limpar, imagem-4.png antiga
       ficaria misturada com o vídeo novo).
    """

    videos_folder = (
        images_folder.parent / "videos"
    )

    if videos_folder.exists():

        for old_file in videos_folder.glob("*"):

            try:
                old_file.unlink()

            except Exception as error:
                print(
                    "[PERSONA PIPELINE] Não foi possível remover vídeo antigo:",
                    old_file,
                    error
                )

    if images_folder.exists():

        for old_file in images_folder.glob("*"):

            try:
                old_file.unlink()

            except Exception as error:
                print(
                    "[PERSONA PIPELINE] Não foi possível remover imagem antiga:",
                    old_file,
                    error
                )


def generate_persona_media(product, scenes):
    """
    Gera todas as imagens de uma produção.
    Retorna lista dos arquivos criados.
    """

    generated_images = []

    print(
        "[PERSONA PIPELINE] Iniciando geração."
    )

    # Criar ou carregar persona fixa
    reference_image = (
        generate_persona_reference()
    )

    if not reference_image:
        print(
            "[PERSONA PIPELINE] Sem persona referência."
        )
        return generated_images

    images_folder = (
        get_images_folder(product)
    )

    # Limpa restos de execuções anteriores (stock ou persona)
    # antes de gerar qualquer coisa nova.
    clear_old_assets(images_folder)

    counter = 1

    for scene in scenes.get(
        "cenas",
        []
    ):

        output_path = (
            images_folder
            /
            f"imagem-{counter}.png"
        )

        print(
            f"[PERSONA PIPELINE] Cena {counter}:",
            scene.get("tipo")
        )

        try:
            result = generate_persona_image(
                product=product,
                scene=scene,
                reference_image_path=reference_image,
                output_path=output_path
            )

            if result:
                generated_images.append(
                    result
                )
                counter += 1

        except Exception as error:
            print(
                "[PERSONA PIPELINE ERROR]",
                error
            )
            # Continua para próxima cena
            continue

    print(
        "[PERSONA PIPELINE] Imagens criadas:",
        len(generated_images)
    )

    return generated_images


def should_use_persona():
    """
    Define qual pipeline usar.
    Default:
        stock
    Para ativar:
        CONTENT_MODE=persona
    """
    mode = os.getenv(
        "CONTENT_MODE",
        "stock"
    )
    return (
        mode.lower()
        ==
        "persona"
    )