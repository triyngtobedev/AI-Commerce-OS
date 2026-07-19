"""
Narration Engine — orquestra providers de TTS com fallback centralizado.

Fluxo:
    NarrationRequest → NarrationEngine → Provider(s) → AudioResult

SSML documentário (Azure):
    - Voz primária: pt-BR-FranciscaNeural
    - Narração normal: rate="-5%" pitch="-10Hz"
    - Cenas dramáticas (gancho, revelacao): rate="-15%" pitch="-15Hz"
    - Pausa de 0,5s entre cenas
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

# Voz e prosódia documentária dramática
DOCUMENTARY_VOICE = "pt-BR-FranciscaNeural"
NORMAL_RATE = "-5%"
NORMAL_PITCH = "-10Hz"
DRAMATIC_RATE = "-15%"
DRAMATIC_PITCH = "-15Hz"
SCENE_PAUSE_SECONDS = 0.5
DRAMATIC_SECTION_KEYS = frozenset({"gancho", "hook", "revelacao"})

VOICE_PRESETS = {
    "documentario_narrado": {
        "voice": DOCUMENTARY_VOICE,
        "rate": NORMAL_RATE,
        "pitch": NORMAL_PITCH,
    },
    "misterio_nao_resolvido": {
        "voice": DOCUMENTARY_VOICE,
        "rate": DRAMATIC_RATE,
        "pitch": DRAMATIC_PITCH,
    },
    "fato_surpreendente": {
        "voice": DOCUMENTARY_VOICE,
        "rate": "-2%",
        "pitch": "-5Hz",
    },
    "revelacao_historica": {
        "voice": DOCUMENTARY_VOICE,
        "rate": DRAMATIC_RATE,
        "pitch": DRAMATIC_PITCH,
    },
    "cronologia_epica": {
        "voice": DOCUMENTARY_VOICE,
        "rate": NORMAL_RATE,
        "pitch": NORMAL_PITCH,
    },
    "impacto_historico": {
        "voice": DOCUMENTARY_VOICE,
        "rate": "-8%",
        "pitch": "-12Hz",
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
                "rate": os.getenv("TTS_RATE", NORMAL_RATE),
                "pitch": os.getenv("TTS_PITCH", NORMAL_PITCH),
            }

        return dict(DEFAULT_PRESET)

    def _section_prosody(self, section_key: str, preset: dict) -> tuple[str, str]:
        if section_key in DRAMATIC_SECTION_KEYS:
            return DRAMATIC_RATE, DRAMATIC_PITCH
        return preset.get("rate", NORMAL_RATE), preset.get("pitch", NORMAL_PITCH)

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
            raw_sections = [sec for sec in parsed.get("sections", []) if sec.get("text")]
            total = len(raw_sections)

            for index, sec in enumerate(raw_sections):
                section_key = sec.get("section_key", "")
                rate, pitch = self._section_prosody(section_key, preset)
                pause_after = SCENE_PAUSE_SECONDS if index < total - 1 else 0.0

                narration_sections.append(
                    NarrationSection(
                        text=sec["text"],
                        emotion=sec.get("emotion", "calm"),
                        intensity=float(sec.get("intensity", 0.5)),
                        section_key=section_key,
                        pause_before=float(sec.get("pause_before", 0.0)),
                        pause_after=pause_after,
                        rate=rate,
                        pitch=pitch,
                    )
                )
            ssml_enabled = bool(narration_sections)

        return NarrationRequest(
            text=prepared,
            output_path=Path(output_path),
            sections=narration_sections,
            voice=preset["voice"],
            rate=preset.get("rate", NORMAL_RATE),
            pitch=preset.get("pitch", NORMAL_PITCH),
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
            f"(normal: rate={NORMAL_RATE}, pitch={NORMAL_PITCH}; "
            f"dramatic: rate={DRAMATIC_RATE}, pitch={DRAMATIC_PITCH}; "
            f"scene pause={SCENE_PAUSE_SECONDS}s)"
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
