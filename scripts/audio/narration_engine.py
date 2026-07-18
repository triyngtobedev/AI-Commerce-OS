"""
Narration Engine — orquestra providers de TTS com fallback centralizado.

Fluxo:
    NarrationRequest → NarrationEngine → Provider(s) → AudioResult

Para adicionar um novo provider (Google, OpenAI, ElevenLabs):
    1. Criar classe em scripts/audio/providers/ implementando NarrationProvider
    2. Registrar na lista DEFAULT_PROVIDERS abaixo
    3. Nenhuma outra parte do pipeline precisa mudar
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from scripts.audio.narration_models import (
    AudioResult,
    NarrationRequest,
    NarrationSection,
)
from scripts.audio.narration_provider import NarrationProvider
from scripts.audio.providers import (
    AzureNarrationProvider,
    EdgeNarrationProvider,
    GTTSNarrationProvider,
)
from scripts.audio.tts_text_prep import prepare_text_for_tts
from scripts.creative.script_parser import parse_script_sections

VOICE_PRESETS = {
    "documentario_narrado": {
        "voice": "pt-BR-AntonioNeural",
        "rate": "-15%",
        "pitch": "-5Hz",
    },
    "misterio_nao_resolvido": {
        "voice": "pt-BR-AntonioNeural",
        "rate": "-15%",
        "pitch": "-6Hz",
    },
    "fato_surpreendente": {
        "voice": "pt-BR-FabioNeural",
        "rate": "-12%",
        "pitch": "-3Hz",
    },
    "revelacao_historica": {
        "voice": "pt-BR-DonatoNeural",
        "rate": "-15%",
        "pitch": "-4Hz",
    },
    "cronologia_epica": {
        "voice": "pt-BR-AntonioNeural",
        "rate": "-14%",
        "pitch": "-3Hz",
    },
    "impacto_historico": {
        "voice": "pt-BR-ThalitaNeural",
        "rate": "-15%",
        "pitch": "-4Hz",
    },
}

DEFAULT_PRESET = VOICE_PRESETS["documentario_narrado"]

DEFAULT_PROVIDERS: list[NarrationProvider] = [
    AzureNarrationProvider(),
    EdgeNarrationProvider(),
    GTTSNarrationProvider(),
]


class NarrationEngine:
    """Engine central de narração — único ponto de entrada para TTS no pipeline."""

    def __init__(
        self,
        providers: Optional[list[NarrationProvider]] = None,
    ):
        self.providers = providers or list(DEFAULT_PROVIDERS)

    def resolve_preset(self, narration_style: str = "documentario_narrado") -> dict:
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

    def build_request(
        self,
        text: str,
        output_path: str | Path,
        narration_style: str = "documentario_narrado",
        script_sections: dict | None = None,
        sections: list[NarrationSection] | None = None,
    ) -> NarrationRequest:
        preset = self.resolve_preset(narration_style)
        prepared = prepare_text_for_tts(text)

        narration_sections: list[NarrationSection] = []
        ssml_enabled = False

        if sections:
            narration_sections = sections
            ssml_enabled = True
        elif script_sections:
            parsed = parse_script_sections(script_sections)
            narration_sections = [
                NarrationSection(
                    text=sec["text"],
                    emotion=sec.get("emotion", "calm"),
                    intensity=float(sec.get("intensity", 0.5)),
                    section_key=sec.get("section_key", ""),
                    pause_before=float(sec.get("pause_before", 0.0)),
                    pause_after=float(sec.get("pause_after", 0.0)),
                )
                for sec in parsed.get("sections", [])
                if sec.get("text")
            ]
            ssml_enabled = bool(narration_sections)

        return NarrationRequest(
            text=prepared,
            output_path=Path(output_path),
            sections=narration_sections,
            voice=preset["voice"],
            rate=preset.get("rate", "+0%"),
            pitch=preset.get("pitch", "+0Hz"),
            ssml_enabled=ssml_enabled,
            narration_style=narration_style,
        )

    def synthesize(self, request: NarrationRequest) -> AudioResult:
        """
        Tenta providers em ordem até um ter sucesso.
        Fallback existe APENAS aqui — providers nunca encadeiam uns aos outros.
        """

        candidates = [
            provider
            for provider in self.providers
            if provider.supports(request)
        ]

        if request.ssml_enabled:
            ssml_providers = [p for p in candidates if p.name == "azure-tts"]
            plain_providers = [p for p in candidates if p.name != "azure-tts"]
            ordered = ssml_providers + plain_providers
        else:
            ordered = candidates

        last_result = AudioResult(
            audio_path=str(request.output_path),
            provider="none",
            success=False,
        )

        for provider in ordered:
            print(f"   Tentando {provider.name}...")
            result = provider.synthesize(request)

            if result.success:
                print(f"🎙️ Áudio criado ({provider.name}): {result.audio_path}")
                return result

            print(f"   ⚠️ {provider.name} falhou — próximo provedor")
            last_result = result

        return last_result

    def generate(
        self,
        text: str,
        output_path: str | Path,
        narration_style: str = "documentario_narrado",
        script_sections: dict | None = None,
        sections: list[NarrationSection] | None = None,
    ) -> str:
        """API de conveniência — retorna caminho do áudio ou levanta erro."""

        if not text:
            raise ValueError("Texto para gerar áudio não informado.")

        request = self.build_request(
            text,
            output_path,
            narration_style=narration_style,
            script_sections=script_sections,
            sections=sections,
        )

        preset = self.resolve_preset(narration_style)
        print(
            f"🎙️ Narration Engine: {preset['voice']} "
            f"(rate={preset.get('rate')}, pitch={preset.get('pitch')})"
        )

        result = self.synthesize(request)

        if not result.success:
            raise RuntimeError(
                "Todos os provedores de TTS falharam. "
                "Verifique conexão e dependências "
                "(azure-cognitiveservices-speech, edge-tts, gTTS)."
            )

        return result.audio_path


_default_engine: Optional[NarrationEngine] = None


def get_narration_engine() -> NarrationEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = NarrationEngine()
    return _default_engine
