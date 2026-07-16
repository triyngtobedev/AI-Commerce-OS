"""Provedor Edge-TTS — vozes neurais gratuitas PT-BR."""

from __future__ import annotations

import asyncio
from pathlib import Path

from scripts.audio.narration_models import AudioResult, NarrationRequest
from scripts.audio.narration_provider import NarrationProvider


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
        return AudioResult(
            audio_path=str(output),
            provider=self.name,
            success=success,
        )
