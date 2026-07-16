"""Interface base para provedores de TTS."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class VoiceProvider(ABC):
    """Interface para provedores de TTS."""

    name: str = "base"

    @abstractmethod
    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> bool:
        ...
