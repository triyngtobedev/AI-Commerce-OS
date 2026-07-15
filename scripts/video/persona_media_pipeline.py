"""
Persona Media Pipeline

Pipeline alternativo ao Pexels.
Quando CONTENT_MODE=persona,
gera imagens utilizando a influenciadora virtual.

Mantém compatibilidade total com renderer.py,
pois salva no mesmo padrão:
output/{produto}/assets/images/imagem-N.png

CORREÇÃO (bug fallback):
clear_old_assets agora só é chamado APÓS a primeira
imagem ser gerada com sucesso. Isso evita que o pipeline
apague os assets antigos (stock ou persona anterior) e
depois falhe na geração, deixando a pasta vazia para o
renderer sem nenhuma mídia para trabalhar.
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

    ATENÇÃO: só deve ser chamado após confirmação de que
    a persona gerou ao menos uma imagem com sucesso.
    Chamar antes disso apaga os assets sem garantia de
    reposição, quebrando o fallback para stock.
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

    Só limpa os assets antigos após a primeira imagem
    ser gerada com sucesso — garantindo que o fallback
    para stock tenha mídia disponível caso a persona falhe.
    """

    generated_images = []
    assets_cleared = False

    print(
        "[PERSONA PIPELINE] Iniciando geração."
    )

    # Criar ou carregar persona fixa
    reference_image = (
        generate_persona_reference()
    )

    if not reference_image:
        print(
            "[PERSONA PIPELINE] Sem persona referência. "
            "Assets antigos preservados para fallback."
        )
        return generated_images

    images_folder = (
        get_images_folder(product)
    )

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

                # Primeira imagem gerada com sucesso:
                # agora é seguro limpar os assets antigos.
                if not assets_cleared:
                    print(
                        "[PERSONA PIPELINE] Primeira imagem confirmada. "
                        "Limpando assets antigos..."
                    )
                    clear_old_assets(images_folder)
                    assets_cleared = True

                generated_images.append(result)
                counter += 1

        except Exception as error:
            print(
                "[PERSONA PIPELINE ERROR]",
                error
            )
            # Continua para próxima cena
            continue

    if not generated_images:
        print(
            "[PERSONA PIPELINE] Nenhuma imagem gerada. "
            "Assets antigos preservados para fallback."
        )
    else:
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