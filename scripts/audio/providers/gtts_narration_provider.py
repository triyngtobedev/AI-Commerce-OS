"""Provedor gTTS — fallback online gratuito (qualidade inferior)."""

from __future__ import annotations

from pathlib import Path

from scripts.audio.narration_models import AudioResult, NarrationRequest
from scripts.audio.narration_provider import NarrationProvider


class GTTSNarrationProvider(NarrationProvider):
    name = "gtts"

    def supports(self, request: NarrationRequest) -> bool:
        try:
            from gtts import gTTS  # noqa: F401
        except ImportError:
            return False
        return bool(request.text)

    def synthesize(self, request: NarrationRequest) -> AudioResult:
        output = Path(request.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        try:
            from gtts import gTTS
        except ImportError:
            return AudioResult(
                audio_path=str(output),
                provider=self.name,
                success=False,
                metadata={"error": "gTTS not installed"},
            )

        slow = (
            request.rate.startswith("-")
            and int(request.rate.replace("%", "").replace("-", "") or "0") > 5
        )

        try:
            lang = request.language.split("-")[0] if request.language else "pt"
            tts = gTTS(text=request.text, lang=lang, slow=slow)
            tts.save(str(output))
            success = output.exists() and output.stat().st_size > 0
        except Exception as error:
            return AudioResult(
                audio_path=str(output),
                provider=self.name,
                success=False,
                metadata={"error": str(error)},
            )

        return AudioResult(
            audio_path=str(output),
            provider=self.name,
            success=success,
            metadata={"fallback": True},
        )
