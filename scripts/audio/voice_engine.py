"""
Voice Engine — compatibilidade retroativa.

Delega toda síntese ao NarrationEngine.
Mantido para não quebrar imports existentes.
"""

from __future__ import annotations

from typing import Optional

from scripts.audio.narration_engine import (
    DEFAULT_PRESET,
    VOICE_PRESETS,
    NarrationEngine,
    get_narration_engine,
)
from scripts.audio.voice_provider import VoiceProvider


class VoiceEngine(NarrationEngine):
    """Alias de compatibilidade — use NarrationEngine em código novo."""

    pass


def get_voice_engine() -> NarrationEngine:
    return get_narration_engine()
