"""
Text To Speech Generator

Delega ao Voice Engine modular (Edge-TTS → gTTS fallback).
"""

from pathlib import Path

from scripts.audio.voice_engine import get_voice_engine

DEFAULT_VOICE = "pt-BR-AntonioNeural"


def generate_audio(
    text,
    output_path=None,
    narration_style="documentario_narrado",
):
    """
    Gera áudio real utilizando Edge-TTS.

    Aceita:

    generate_audio(
        "texto",
        "arquivo.mp3"
    )

    ou:

    generate_audio(
        {
            "produto": {},
            "conteudo": {
                "texto_narracao": ""
            }
        }
    )
    """


    # Compatibilidade com pipeline atual

    if isinstance(text, dict):

        data = text


        if "conteudo" in data:

            text = (
                data
                .get("conteudo", {})
                .get(
                    "texto_narracao",
                    ""
                )
            )


        elif "text" in data:

            text = data.get(
                "text",
                ""
            )


        else:

            text = ""


        output_path = (
            data.get(
                "output_path"
            )
            or data.get(
                "output"
            )
            or output_path
        )

        narration_style = (
            data.get("narration_style")
            or narration_style
        )


    if not text:

        raise ValueError(
            "Texto para gerar áudio não informado."
        )

    if output_path is None:
        output_path = "output/audio/audio.mp3"

    engine = get_voice_engine()

    return engine.generate(
        text,
        output_path,
        narration_style=narration_style,
    )



create_audio = generate_audio