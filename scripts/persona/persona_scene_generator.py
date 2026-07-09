"""
Persona Scene Generator

Gera imagens da persona virtual em diferentes cenas.

Recebe:
- imagem referência da persona
- produto
- descrição visual da cena

Retorna:
- nova imagem mantendo identidade visual da persona
"""

import os
import time
from pathlib import Path
from datetime import date

from google import genai
from google.genai import types


MODEL_NAME = "gemini-2.5-flash-image"


# Controle simples de consumo diário
USAGE_DIR = Path("database/persona")
USAGE_FILE = USAGE_DIR / "image_usage.txt"


def get_gemini_client():
    """
    Inicializa cliente Gemini.
    """

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY não encontrada."
        )

    return genai.Client(
        api_key=api_key
    )


def get_daily_limit():
    """
    Limite configurável por ambiente.
    """

    return int(
        os.getenv(
            "GEMINI_IMAGE_DAILY_LIMIT",
            "20"
        )
    )


def get_today_usage():
    """
    Lê quantidade de imagens geradas hoje.
    """

    if not USAGE_FILE.exists():
        return 0

    try:
        content = USAGE_FILE.read_text()

        saved_date, amount = content.split("|")

        if saved_date != str(date.today()):
            return 0

        return int(amount)

    except Exception:
        return 0


def increment_usage():
    """
    Incrementa contador diário.
    """

    USAGE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    current = get_today_usage()

    USAGE_FILE.write_text(
        f"{date.today()}|{current + 1}"
    )


def check_daily_limit():

    current = get_today_usage()
    limit = get_daily_limit()

    if current >= limit:
        print(
            "[PERSONA] Limite diário atingido."
        )
        return False

    return True


def build_scene_prompt(product, scene):
    """
    Monta instrução para edição da imagem.
    """

    return f"""
Use the provided reference image as the exact identity anchor.

Keep the same person:
- same face
- same hair
- same age
- same body characteristics
- same visual identity

Transform this person into a Brazilian TikTok shopping creator.

Product:
{product.get("nome")}

Product category:
{product.get("categoria", "consumer product")}

Scene description:
{scene.get("visual")}

Requirements:
- The person must hold or interact naturally with the product.
- Make the product clearly visible.
- Realistic photography.
- Natural lighting.
- Authentic social media content style.
- Vertical TikTok style composition.
- No text.
- No logos added.
- Do not change the person's identity.
"""


def generate_persona_image(
    product,
    scene,
    reference_image_path,
    output_path
):
    """
    Gera uma imagem da persona em uma cena.

    Retorna:
        caminho do arquivo gerado
        ou None em caso de erro.
    """

    if not check_daily_limit():
        return None

    reference = Path(
        reference_image_path
    )

    if not reference.exists():
        print(
            "[PERSONA] Referência não encontrada."
        )
        return None

    retries = 3

    for attempt in range(retries):

        try:
            client = get_gemini_client()

            with open(
                reference,
                "rb"
            ) as image_file:
                image_bytes = image_file.read()

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[

                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type="image/png"
                    ),

                    build_scene_prompt(
                        product,
                        scene
                    )

                ],

                config=types.GenerateContentConfig(
                    response_modalities=[
                        "IMAGE"
                    ],
                    image_config=types.ImageConfig(
                        aspect_ratio="9:16"
                    )
                )
            )

            generated_image = None

            for part in response.parts:
                if part.inline_data:
                    generated_image = (
                        part.inline_data.data
                    )
                    break

            if not generated_image:
                raise RuntimeError(
                    "Gemini não retornou imagem."
                )

            output = Path(
                output_path
            )

            output.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            with open(
                output,
                "wb"
            ) as file:
                file.write(
                    generated_image
                )

            increment_usage()

            print(
                "[PERSONA] Cena criada:",
                output
            )

            return str(output)

        except Exception as error:

            import traceback


            print(
                f"[PERSONA ERROR] Tentativa {attempt + 1}/{retries}:",
                error
            )

            traceback.print_exc()

            if attempt < retries - 1:
                wait_time = (
                    2 ** attempt
                )
                time.sleep(
                    wait_time
                )

    print(
        "[PERSONA] Falha definitiva na geração da cena."
    )

    return None