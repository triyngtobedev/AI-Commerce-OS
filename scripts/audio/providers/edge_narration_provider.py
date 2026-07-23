"""Provedor Edge-TTS — vozes neurais gratuitas PT-BR com SSML e pós-processamento."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Any

from scripts.audio.narration_models import AudioResult, NarrationRequest
from scripts.audio.narration_provider import NarrationProvider


# Pós-processamento: EQ + compressão + normalização LUFS -16 (padrão YouTube)
def post_process_audio(input_path: Path, output_path: Path | None = None) -> Path:
    """
    Aplica EQ (boost 2-4kHz para presença vocal), compressão suave
    e normalização LUFS -16 integrada para YouTube.

    Em caso de falha (ffmpeg, disco, permissão), retorna o áudio original intacto.
    """
    if not input_path.exists():
        return input_path

    target = output_path or input_path
    if target == input_path:
        temp = input_path.with_suffix(".tmp.mp3")
    else:
        temp = target

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-af",
        "equalizer=f=80:t=h:width=0.5:g=-6,"
        "equalizer=f=2500:t=q:width=1:g=4,"
        "equalizer=f=6000:t=q:width=1:g=2,"
        "acompressor=threshold=0.3:ratio=3:attack=5:release=50,"
        "loudnorm=I=-16:TP=-1.5:LRA=7",
        "-c:a", "libmp3lame",
        "-q:a", "2",
        str(temp),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        if temp.exists():
            if temp != target:
                temp.replace(target)
        else:
            print("  ⚠️ Pós-processamento de áudio: ffmpeg não produziu saída — usando áudio bruto")
            return target
    except Exception as exc:
        print(f"  ⚠️ Pós-processamento de áudio falhou ({exc}) — usando áudio bruto")
        if temp.exists():
            temp.unlink()

    return target


def _escape_ssml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _build_edge_ssml(request: NarrationRequest) -> str:
    """Constrói SSML compatível com Edge TTS a partir das seções narradas.

    Edge TTS suporta: <prosody>, <break>, <emphasis>, <phoneme>.
    NÃO suporta: <mstts:express-as> (Azure-only).
    """
    parts: list[str] = []

    for index, section in enumerate(request.sections):
        text = section.text if hasattr(section, "text") else section.get("text", "")
        if not text:
            continue

        escaped = _escape_ssml(text)

        rate = getattr(section, "rate", "") or request.rate
        pitch = getattr(section, "pitch", "") or request.pitch
        pause_before = float(getattr(section, "pause_before", 0) if hasattr(section, "pause_before") else section.get("pause_before", 0))
        pause_after = float(getattr(section, "pause_after", 0) if hasattr(section, "pause_after") else section.get("pause_after", 0))

        if pause_before > 0:
            parts.append(f'<break time="{int(pause_before * 1000)}ms"/>')
        elif index > 0:
            parts.append('<break time="400ms"/>')

        parts.append(
            f'<prosody rate="{rate}" pitch="{pitch}">'
            f'{escaped}'
            f'</prosody>'
        )

        if index < len(request.sections) - 1:
            if pause_after > 0:
                parts.append(f'<break time="{int(pause_after * 1000)}ms"/>')

    body = "\n    ".join(parts)
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        f'xml:lang="{request.language}">\n'
        f'  <voice name="{request.voice}">\n'
        f"    {body}\n"
        f"  </voice>\n"
        f"</speak>"
    )


class EdgeNarrationProvider(NarrationProvider):
    name = "edge-tts"

    def supports(self, request: NarrationRequest) -> bool:
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            return False
        return bool(request.text)

    def synthesize(self, request: NarrationRequest) -> AudioResult:
        output = Path(request.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        try:
            import edge_tts
        except ImportError:
            return AudioResult(
                audio_path=str(output),
                provider=self.name,
                success=False,
                metadata={"error": "edge-tts not installed"},
            )

        async def _run():
            if request.ssml_enabled and request.sections:
                ssml = _build_edge_ssml(request)
                # edge-tts aceita SSML como primeiro argumento (text=)
                # rate/pitch não são passados pois já estão nas tags <prosody>
                communicate = edge_tts.Communicate(
                    ssml,
                    voice=request.voice,
                )
            else:
                communicate = edge_tts.Communicate(
                    text=request.text,
                    voice=request.voice,
                    rate=request.rate,
                    pitch=request.pitch,
                )
            await communicate.save(str(output))

        try:
            asyncio.run(_run())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_run())
            loop.close()

        success = output.exists() and output.stat().st_size > 0
        if success:
            post_process_audio(output)

        return AudioResult(
            audio_path=str(output),
            provider=self.name,
            success=success,
        )
