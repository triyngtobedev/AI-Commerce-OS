"""
Provedor Azure — compatibilidade retroativa.

Implementação real em providers/azure_narration_provider.py.
"""

from __future__ import annotations

from pathlib import Path

from scripts.audio.narration_models import NarrationRequest
from scripts.audio.providers.azure_narration_provider import AzureNarrationProvider
from scripts.audio.voice_provider import VoiceProvider


class AzureTTSProvider(VoiceProvider):
    """Wrapper legado — delega ao AzureNarrationProvider."""

    name = "azure-tts"

    def __init__(self):
        self._provider = AzureNarrationProvider()

    def synthesize_ssml(self, ssml: str, output_path: Path) -> bool:
        return self._provider._synthesize_ssml(ssml, output_path)

    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> bool:
        request = NarrationRequest(
            text=text,
            output_path=output_path,
            voice=voice,
            rate=rate,
            pitch=pitch,
        )
        result = self._provider.synthesize(request)
        return result.success
