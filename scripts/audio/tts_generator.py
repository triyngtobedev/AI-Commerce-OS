"""
Text To Speech Generator

Responsável por gerar áudio a partir de texto.
"""

from pathlib import Path


def generate_audio(text, output_path=None):
    """
    Gera arquivo de áudio.

    Aceita:
    generate_audio("texto", "arquivo.mp3")

    ou

    generate_audio({"text": "texto", "output": "arquivo.mp3"})
    """

    if isinstance(text, dict):
        data = text

        text = data.get("text", "")
        output_path = data.get(
            "output_path",
            data.get("output", output_path)
        )

    if output_path is None:
        output_path = "output/audio/audio.mp3"

    output = Path(output_path)

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # MOCK TEMPORÁRIO
    # Aqui entra a IA de voz depois

    with open(output, "wb") as file:
        file.write(b"")

    print(f"🎙️ Áudio criado: {output}")

    return str(output)


create_audio = generate_audio