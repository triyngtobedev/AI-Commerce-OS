"""
Teste isolado do sistema de Persona IA.

Valida:

1. Criação ou carregamento da persona referência.
2. Geração de uma imagem de cena usando a persona.
3. Integridade dos arquivos gerados.

Não integra com pipeline de produção.
"""

import os
from pathlib import Path

from PIL import Image


from scripts.persona.persona_generator import (
    generate_persona_reference
)

from scripts.persona.persona_scene_generator import (
    generate_persona_image
)



# Arquivo temporário apenas para teste
TEST_OUTPUT = Path(
    "database/persona/test_scene.png"
)



def check_api_key():

    """
    Verifica API antes de qualquer chamada Gemini.
    """

    if not os.getenv(
        "GEMINI_API_KEY"
    ):

        print(
            "❌ ERRO: GEMINI_API_KEY não encontrada."
        )

        print(
            "Configure a variável de ambiente antes de executar o teste."
        )

        return False


    return True



def validate_image(path):

    """
    Abre imagem com PIL para validar integridade.
    """

    try:

        with Image.open(path) as image:

            width, height = image.size


            return {
                "ok": True,
                "width": width,
                "height": height
            }


    except Exception as error:

        print(
            "Erro validando imagem:",
            error
        )

        return {
            "ok": False
        }



def main():

    print(
        "\n================================"
    )

    print(
        " TESTE PERSONA IA"
    )

    print(
        "================================\n"
    )


    failed_step = None



    # --------------------------------
    # 1. Validar API KEY
    # --------------------------------

    if not check_api_key():

        return



    reference_path = None


    # --------------------------------
    # 2. Gerar/carregar persona
    # --------------------------------

    try:

        print(
            "🤖 Verificando persona referência..."
        )


        reference_path = (
            generate_persona_reference()
        )


        if not reference_path:

            failed_step = (
                "generate_persona_reference"
            )

            raise Exception(
                "Persona não retornada."
            )



        reference_file = Path(
            reference_path
        )


        size_kb = (
            reference_file.stat().st_size
            /
            1024
        )


        print(
            f"📁 Referência: {reference_path}"
        )


        if size_kb < 1:

            print(
                "⚠️ Arquivo parece vazio."
            )

        else:

            print(
                f"📦 Tamanho: {size_kb:.2f} KB"
            )



    except Exception as error:

        failed_step = (
            failed_step
            or
            "referência persona"
        )


        print(
            "❌ Falha na referência:",
            error
        )



    if not reference_path:

        print(
            "\n❌ Teste encerrado."
        )

        return



    # --------------------------------
    # 3. Gerar cena teste
    # --------------------------------

    product = {
        "nome": "Mini Aspirador Portátil",
        "categoria": "Casa"
    }


    scene = {
        "tempo": "0-3",
        "tipo": "hook",
        "visual":
            (
                "person using a mini vacuum cleaner "
                "on a car dashboard, close up, "
                "satisfying clean result"
            )
    }



    try:

        print(
            "\n🎬 Gerando cena teste..."
        )


        generated = generate_persona_image(
            product=product,
            scene=scene,
            reference_image_path=reference_path,
            output_path=TEST_OUTPUT
        )


        if not generated:

            failed_step = (
                "generate_persona_image"
            )

            raise Exception(
                "Imagem da cena não foi gerada."
            )


        print(
            f"📁 Cena criada: {generated}"
        )



    except Exception as error:

        failed_step = (
            failed_step
            or
            "cena persona"
        )


        print(
            "❌ Falha na cena:",
            error
        )



    # --------------------------------
    # 4. Validar imagens com PIL
    # --------------------------------


    print(
        "\n🔎 Validando arquivos..."
    )


    reference_check = validate_image(
        Path(reference_path)
    )


    scene_check = validate_image(
        TEST_OUTPUT
    )



    # --------------------------------
    # Resultado final
    # --------------------------------


    print(
        "\n================================"
    )

    print(
        " RESULTADO FINAL"
    )

    print(
        "================================"
    )


    if reference_check["ok"]:

        size = (
            Path(reference_path)
            .stat()
            .st_size
            /
            1024
        )

        print(
            f"✅ Referência: OK ({size:.2f} KB)"
        )

    else:

        print(
            "❌ Referência: inválida"
        )



    if scene_check["ok"]:

        print(
            "✅ Cena de teste: OK "
            f"({scene_check['width']}x{scene_check['height']})"
        )

    else:

        print(
            "❌ Cena de teste: inválida"
        )



    if failed_step:

        print(
            f"\n❌ Falhou em: {failed_step}"
        )

    else:

        print(
            "\n🎉 Persona IA funcionando corretamente."
        )



if __name__ == "__main__":

    main()