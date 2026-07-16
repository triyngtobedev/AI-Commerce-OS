"""
Modelos compartilhados do Narration Engine.

Todo o pipeline deve consumir apenas NarrationEngine — nunca providers diretamente.
Novos providers (Google, OpenAI, ElevenLabs, etc.) entram implementando NarrationProvider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class NarrationSection:
    """Trecho narrado com metadados emocionais."""

    text: str
    emotion: str = "calm"
    intensity: float = 0.5
    section_key: str = ""
    pause_before: float = 0.0
    pause_after: float = 0.0


@dataclass
class NarrationRequest:
    """Pedido unificado de síntese de voz."""

    text: str
    output_path: Path
    sections: list[NarrationSection] = field(default_factory=list)
    language: str = "pt-BR"
    voice: str = "pt-BR-AntonioNeural"
    emotion_data: Optional[dict[str, Any]] = None
    ssml_enabled: bool = False
    provider_options: dict[str, Any] = field(default_factory=dict)
    rate: str = "+0%"
    pitch: str = "+0Hz"
    narration_style: str = "documentario_narrado"


@dataclass
class AudioResult:
    """Resultado padronizado de qualquer provider de TTS."""

    audio_path: str
    provider: str
    duration: float = 0.0
    success: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
