"""
Text To Speech Generator

Responsável por gerar áudio real usando Edge-TTS.
"""

from pathlib import Path
import asyncio

import edge_tts


DEFAULT_VOICE = "pt-BR-FranciscaNeural"


async def _generate(
    text,
    output_path,
    voice=DEFAULT_VOICE
):

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice
    )

    await communicate.save(
        output_path
    )


def generate_audio(
    text,
    output_path=None
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


    if not text:

        raise ValueError(
            "Texto para gerar áudio não informado."
        )


    if output_path is None:

        output_path = (
            "output/audio/audio.mp3"
        )


    output = Path(output_path)


    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    try:

        asyncio.run(
            _generate(
                text,
                str(output)
            )
        )


    except RuntimeError:

        loop = asyncio.new_event_loop()

        loop.run_until_complete(
            _generate(
                text,
                str(output)
            )
        )

        loop.close()



    print(
        f"🎙️ Áudio criado: {output}"
    )


    return str(output)



create_audio = generate_audio