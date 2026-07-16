"""Testes para Narration Engine — providers mockados, sem APIs reais."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.audio.narration_engine import NarrationEngine
from scripts.audio.narration_models import AudioResult, NarrationRequest, NarrationSection
from scripts.audio.narration_provider import NarrationProvider


class MockSuccessProvider(NarrationProvider):
    name = "mock-success"

    def supports(self, request: NarrationRequest) -> bool:
        return True

    def synthesize(self, request: NarrationRequest) -> AudioResult:
        output = Path(request.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake-audio")
        return AudioResult(
            audio_path=str(output),
            provider=self.name,
            success=True,
        )


class MockFailProvider(NarrationProvider):
    name = "mock-fail"

    def supports(self, request: NarrationRequest) -> bool:
        return True

    def synthesize(self, request: NarrationRequest) -> AudioResult:
        return AudioResult(
            audio_path=str(request.output_path),
            provider=self.name,
            success=False,
        )


class TestNarrationEngine(unittest.TestCase):

    def setUp(self):
        self.print_patcher = patch("scripts.audio.narration_engine.print")
        self.print_patcher.start()

    def tearDown(self):
        self.print_patcher.stop()

    def test_fallback_to_second_provider(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "audio.mp3"
            engine = NarrationEngine(providers=[
                MockFailProvider(),
                MockSuccessProvider(),
            ])
            request = NarrationRequest(
                text="Teste de narração.",
                output_path=output,
            )
            result = engine.synthesize(request)
            self.assertTrue(result.success)
            self.assertEqual(result.provider, "mock-success")

    def test_all_providers_fail(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "audio.mp3"
            engine = NarrationEngine(providers=[MockFailProvider()])
            request = NarrationRequest(text="Teste.", output_path=output)
            result = engine.synthesize(request)
            self.assertFalse(result.success)

    def test_build_request_from_script_sections(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "audio.mp3"
            engine = NarrationEngine(providers=[])
            script = {
                "hook": "A explosão aconteceu em 1908.",
                "contexto": "A Sibéria era remota.",
            }
            request = engine.build_request(
                "A explosão aconteceu em 1908. A Sibéria era remota.",
                output,
                script_sections=script,
            )
            self.assertTrue(request.ssml_enabled)
            self.assertEqual(len(request.sections), 2)
            self.assertEqual(request.sections[0].emotion, "impact")

    def test_generate_raises_when_all_fail(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "audio.mp3"
            engine = NarrationEngine(providers=[MockFailProvider()])
            with self.assertRaises(RuntimeError):
                engine.generate("Texto.", output)

    def test_ssml_prefers_azure_provider_order(self):
        call_order = []

        class TrackingProvider(NarrationProvider):
            def __init__(self, name):
                self.name = name

            def supports(self, request):
                return True

            def synthesize(self, request):
                call_order.append(self.name)
                return AudioResult(
                    audio_path=str(request.output_path),
                    provider=self.name,
                    success=self.name == "azure-tts",
                )

        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "audio.mp3"
            engine = NarrationEngine(providers=[
                TrackingProvider("edge-tts"),
                TrackingProvider("azure-tts"),
            ])
            request = NarrationRequest(
                text="Teste SSML.",
                output_path=output,
                ssml_enabled=True,
                sections=[NarrationSection(text="Teste.", emotion="mystery")],
            )
            result = engine.synthesize(request)
            self.assertTrue(result.success)
            self.assertEqual(call_order[0], "azure-tts")


if __name__ == "__main__":
    unittest.main()
