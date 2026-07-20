import os
import soundfile as sf
import numpy as np


def generate_narration_kokoro(
    text: str,
    output_path: str,
    voice: str = "bf_alice",
    speed: float = 0.85,
) -> str:
    """
    Generate dramatic narration using Kokoro TTS.
    voice options for PT-BR dramatic style:
    - "bf_alice" — female, clear
    - "bm_daniel" — male, deep
    - "af_heart" — female, emotional
    speed: 0.85 = slightly slower = more dramatic
    """
    from kokoro import KPipeline

    pipeline = KPipeline(lang_code="p")  # "p" = Portuguese

    samples = []
    sample_rate = 24000

    generator = pipeline(text, voice=voice, speed=speed, split_pattern=r"\n+")
    for i, (gs, ps, audio) in enumerate(generator):
        samples.append(audio)

    if samples:
        full_audio = np.concatenate(samples)
        sf.write(output_path, full_audio, sample_rate)
        return output_path
    else:
        raise RuntimeError("Kokoro returned no audio")
