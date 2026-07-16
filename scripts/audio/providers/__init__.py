"""Provedores de narração desacoplados."""

from scripts.audio.providers.azure_narration_provider import AzureNarrationProvider
from scripts.audio.providers.edge_narration_provider import EdgeNarrationProvider
from scripts.audio.providers.gtts_narration_provider import GTTSNarrationProvider

__all__ = [
    "AzureNarrationProvider",
    "EdgeNarrationProvider",
    "GTTSNarrationProvider",
]
