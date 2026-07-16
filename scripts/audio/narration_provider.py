"""
Interface unificada para provedores de narração.

Cada provider implementa exatamente a mesma interface.
Providers NÃO conhecem outros providers — fallback fica no NarrationEngine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from scripts.audio.narration_models import AudioResult, NarrationRequest


class NarrationProvider(ABC):
    """Contrato que todo provider de TTS deve implementar."""

    name: str = "base"

    @abstractmethod
    def supports(self, request: NarrationRequest) -> bool:
        """Indica se o provider pode atender este pedido."""

    @abstractmethod
    def synthesize(self, request: NarrationRequest) -> AudioResult:
        """Sintetiza áudio. Retorna AudioResult — nunca levanta para fallback."""
