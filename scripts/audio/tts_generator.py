"""
Text To Speech Generator

Delega ao Narration Engine (único ponto de entrada para TTS no pipeline).
"""

from pathlib import Path

from scripts.audio.narration_engine import get_narration_engine
from scripts.audio.narration_models import NarrationSection
from scripts.core.emotional_timeline import EmotionalTimeline

DEFAULT_VOICE = "pt-BR-AntonioNeural"


def generate_audio(
    text,
    output_path=None,
    narration_style="documentario_narrado",
    script_sections=None,
    emotional_timeline=None,
):
    """
    Gera áudio real utilizando Narration Engine.

    Aceita texto simples, dict de pipeline ou EmotionalTimeline.
    """

    sections = None

    if isinstance(text, dict):
        data = text
        emotional_timeline = emotional_timeline or data.get("emotional_timeline")

        if "conteudo" in data:
            text = data.get("conteudo", {}).get("texto_narracao", "")
        elif "text" in data:
            text = data.get("text", "")
        else:
            text = ""

        output_path = data.get("output_path") or data.get("output") or output_path
        narration_style = data.get("narration_style") or narration_style
        script_sections = data.get("script_sections") or script_sections

    if emotional_timeline:
        if isinstance(emotional_timeline, dict):
            emotional_timeline = EmotionalTimeline.from_dict(emotional_timeline)

        sections = [
            NarrationSection(
                text=sec.text,
                emotion=sec.emotion,
                intensity=sec.intensity,
                section_key=sec.section_key,
                pause_before=sec.pause_before,
                pause_after=sec.pause_after,
            )
            for sec in emotional_timeline.sections
        ]

    if not text:
        raise ValueError("Texto para gerar áudio não informado.")

    if output_path is None:
        output_path = "output/audio/audio.mp3"

    engine = get_narration_engine()

    return engine.generate(
        text,
        output_path,
        narration_style=narration_style,
        script_sections=script_sections,
        sections=sections,
    )


create_audio = generate_audio
