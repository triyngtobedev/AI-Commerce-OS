"""
Persona Generator
Responsável por criar a imagem base da influenciadora virtual.
A persona é gerada uma única vez e reutilizada em todas
as cenas futuras para manter consistência visual.
"""

import os
from pathlib import Path

from google import genai
from google.genai import types

from scripts.utils.prompt_loader import load_prompt


# Caminho fixo da referência da persona
PERSONA_DIR = Path("database/persona")
REFERENCE_IMAGE = PERSONA_DIR / "reference.png"

# Modelo de imagem Gemini
MODEL_NAME = "gemini-2.5-flash-image"


def get_gemini_client():
    """
    Inicializa cliente Gemini usando variável de ambiente.
    """

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY não encontrada nas variáveis de ambiente."
        )

    return genai.Client(api_key=api_key)


def load_persona_prompt():
    """
    Carrega o prompt da persona a partir de prompts/persona_reference.md
    """

    return load_prompt("persona_reference")


def generate_persona_reference():
    """
    Cria a imagem base da persona.

    Se já existir:
        retorna o caminho existente.
    Se não existir:
        gera usando Gemini Image e salva em disco.
    """

    # Cache local
    if REFERENCE_IMAGE.exists():
        print(
            "[PERSONA] Referência encontrada no cache."
        )
        return str(REFERENCE_IMAGE)

    print(
        "[PERSONA] Criando nova persona..."
    )

    try:
        client = get_gemini_client()

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                load_persona_prompt()
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

        image_data = None

        for part in response.parts:
            if part.inline_data:
                image_data = part.inline_data.data
                break

        if not image_data:
            raise RuntimeError(
                "Gemini não retornou imagem da persona."
            )

        # Criar pasta
        PERSONA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        # Salvar imagem
        with open(
            REFERENCE_IMAGE,
            "wb"
        ) as file:
            file.write(image_data)

        print(
            "[PERSONA] Persona criada com sucesso:",
            REFERENCE_IMAGE
        )

        return str(REFERENCE_IMAGE)

    except Exception as error:
        print(
            "[PERSONA ERROR]",
            error
        )

        # Não quebra o pipeline
        return None