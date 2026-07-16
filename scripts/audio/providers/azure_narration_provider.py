"""
Provedor Azure Cognitive Services Speech SDK.

Suporta SSML completo — único provider que aceita ssml_enabled=True.
"""

from __future__ import annotations

import os
from pathlib import Path

from scripts.audio.narration_models import AudioResult, NarrationRequest
from scripts.audio.narration_provider import NarrationProvider
from scripts.audio.ssml_builder import build_ssml_from_sections, escape_ssml


class AzureNarrationProvider(NarrationProvider):
    name = "azure-tts"

    def _credentials_configured(self) -> bool:
        return bool(os.getenv("AZURE_SPEECH_KEY") and os.getenv("AZURE_SPEECH_REGION"))

    def supports(self, request: NarrationRequest) -> bool:
        if not self._credentials_configured():
            return False
        if request.ssml_enabled and not request.sections:
            return False
        return True

    def synthesize(self, request: NarrationRequest) -> AudioResult:
        output = Path(request.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        if request.ssml_enabled and request.sections:
            ssml = build_ssml_from_sections(
                request.sections,
                request.voice,
                request.rate,
                request.pitch,
            )
            if ssml:
                success = self._synthesize_ssml(ssml, output)
                return AudioResult(
                    audio_path=str(output),
                    provider=self.name,
                    success=success,
                    metadata={"ssml": True},
                )

        ssml = self._plain_text_ssml(request)
        success = self._synthesize_ssml(ssml, output)
        return AudioResult(
            audio_path=str(output),
            provider=self.name,
            success=success,
            metadata={"ssml": False},
        )

    def _plain_text_ssml(self, request: NarrationRequest) -> str:
        safe_text = escape_ssml(request.text)
        return (
            f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            f'xml:lang="{request.language}">'
            f'<voice name="{request.voice}">'
            f'<prosody rate="{request.rate}" pitch="{request.pitch}">{safe_text}</prosody>'
            f"</voice></speak>"
        )

    def _synthesize_ssml(self, ssml: str, output_path: Path) -> bool:
        if not ssml:
            return False

        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError:
            return False

        speech_config = speechsdk.SpeechConfig(
            subscription=os.getenv("AZURE_SPEECH_KEY"),
            region=os.getenv("AZURE_SPEECH_REGION"),
        )
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
        )

        audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_path))
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )

        try:
            result = synthesizer.speak_ssml_async(ssml).get()
        except Exception:
            return False

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return output_path.exists() and output_path.stat().st_size > 0

        return False
