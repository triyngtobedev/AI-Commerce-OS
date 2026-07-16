"""
Voice Engine — síntese de voz modular com fallback automático.

Provedores (ordem de tentativa):
  1. Edge-TTS (gratuito, vozes neurais PT-BR)
  2. gTTS (gratuito, Google — fallback online)
"""

from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from scripts.audio.tts_text_prep import prepare_text_for_tts


# Vozes documentais PT-BR (Edge-TTS — gratuitas)
VOICE_PRESETS = {
    "documentario_narrado": {
        "voice": "pt-BR-AntonioNeural",
        "rate": "-4%",
        "pitch": "-3Hz",
    },
    "misterio_nao_resolvido": {
        "voice": "pt-BR-AntonioNeural",
        "rate": "-8%",
        "pitch": "-5Hz",
    },
    "fato_surpreendente": {
        "voice": "pt-BR-FabioNeural",
        "rate": "-2%",
        "pitch": "+0Hz",
    },
    "revelacao_historica": {
        "voice": "pt-BR-DonatoNeural",
        "rate": "-5%",
        "pitch": "-2Hz",
    },
    "cronologia_epica": {
        "voice": "pt-BR-AntonioNeural",
        "rate": "-3%",
        "pitch": "-1Hz",
    },
    "impacto_historico": {
        "voice": "pt-BR-ThalitaNeural",
        "rate": "-4%",
        "pitch": "-2Hz",
    },
}

DEFAULT_PRESET = VOICE_PRESETS["documentario_narrado"]


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


class EdgeTTSProvider(VoiceProvider):
    name = "edge-tts"

    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> bool:
        try:
            import edge_tts
        except ImportError:
            return False

        async def _run():
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                pitch=pitch,
            )
            await communicate.save(str(output_path))

        try:
            asyncio.run(_run())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_run())
            loop.close()

        return output_path.exists() and output_path.stat().st_size > 0


class GTTSProvider(VoiceProvider):
    """Fallback gratuito via Google TTS (requer internet)."""

    name = "gtts"

    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> bool:
        try:
            from gtts import gTTS
        except ImportError:
            print("⚠️ gTTS não instalado — pip install gTTS")
            return False

        slow = rate.startswith("-") and int(rate.replace("%", "").replace("-", "") or "0") > 5

        try:
            tts = gTTS(text=text, lang="pt", slow=slow)
            tts.save(str(output_path))
            return output_path.exists() and output_path.stat().st_size > 0
        except Exception as error:
            print(f"⚠️ gTTS falhou: {error}")
            return False


class VoiceEngine:
    """
    Engine central de narração.
    Seleciona voz por estilo de conteúdo e tenta provedores em cadeia.
    """

    def __init__(
        self,
        providers: Optional[list[VoiceProvider]] = None,
    ):
        self.providers = providers or [
            EdgeTTSProvider(),
            GTTSProvider(),
        ]

    def resolve_preset(self, narration_style: str = "documentario_narrado") -> dict:
        """Retorna preset de voz para o estilo narrativo."""

        preset = VOICE_PRESETS.get(narration_style)
        if preset:
            return dict(preset)

        env_voice = os.getenv("TTS_VOICE")
        if env_voice:
            return {
                "voice": env_voice,
                "rate": os.getenv("TTS_RATE", "-4%"),
                "pitch": os.getenv("TTS_PITCH", "-3Hz"),
            }

        return dict(DEFAULT_PRESET)

    def generate(
        self,
        text: str,
        output_path: str | Path,
        narration_style: str = "documentario_narrado",
    ) -> str:
        """
        Gera áudio de narração com fallback automático entre provedores.
        """

        if not text:
            raise ValueError("Texto para gerar áudio não informado.")

        prepared = prepare_text_for_tts(text)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        preset = self.resolve_preset(narration_style)
        voice = preset["voice"]
        rate = preset.get("rate", "+0%")
        pitch = preset.get("pitch", "+0Hz")

        print(
            f"🎙️ Voice Engine: {voice} "
            f"(rate={rate}, pitch={pitch})"
        )

        for provider in self.providers:
            print(f"   Tentando {provider.name}...")

            if provider.synthesize(prepared, output, voice, rate, pitch):
                print(f"🎙️ Áudio criado ({provider.name}): {output}")
                return str(output)

            print(f"   ⚠️ {provider.name} falhou — próximo provedor")

        raise RuntimeError(
            "Todos os provedores de TTS falharam. "
            "Verifique conexão e dependências (edge-tts, gTTS)."
        )


_default_engine: Optional[VoiceEngine] = None


def get_voice_engine() -> VoiceEngine:
    """Retorna instância singleton do Voice Engine."""

    global _default_engine
    if _default_engine is None:
        _default_engine = VoiceEngine()
    return _default_engine
