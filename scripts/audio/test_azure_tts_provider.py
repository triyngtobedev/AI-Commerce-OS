"""Testes para Azure TTS provider (mock — sem chamadas de rede)."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.audio.azure_tts_provider import AzureTTSProvider


def _mock_speechsdk():
    """Cria módulo mock do Azure Speech SDK."""

    mock = MagicMock()
    mock.ResultReason.SynthesizingAudioCompleted = "completed"
    mock.ResultReason.Canceled = "canceled"
    mock.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3 = "mp3"
    return mock


def _patch_azure_modules(mock_speechsdk):
    """Injeta módulos azure mockados para import local dentro do provider."""

    azure_mod = MagicMock()
    cognitiveservices_mod = MagicMock()
    cognitiveservices_mod.speech = mock_speechsdk
    azure_mod.cognitiveservices = cognitiveservices_mod

    return patch.dict(
        sys.modules,
        {
            "azure": azure_mod,
            "azure.cognitiveservices": cognitiveservices_mod,
            "azure.cognitiveservices.speech": mock_speechsdk,
        },
    )


class TestAzureTTSProvider(unittest.TestCase):

    def test_returns_false_without_credentials(self):
        provider = AzureTTSProvider()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "audio.mp3"
            with patch.dict("os.environ", {}, clear=True):
                with patch("builtins.print"):
                    result = provider.synthesize_ssml(
                        '<speak version="1.0">test</speak>',
                        output,
                    )
            self.assertFalse(result)
            self.assertFalse(output.exists())

    def test_synthesize_ssml_calls_sdk_with_expected_params(self):
        mock_speechsdk = _mock_speechsdk()

        mock_result = MagicMock()
        mock_result.reason = mock_speechsdk.ResultReason.SynthesizingAudioCompleted

        mock_synth = MagicMock()
        mock_synth.speak_ssml_async.return_value.get.return_value = mock_result
        mock_speechsdk.SpeechSynthesizer.return_value = mock_synth

        provider = AzureTTSProvider()
        ssml = (
            '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis">'
            '<voice name="pt-BR-AntonioNeural">teste</voice></speak>'
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "audio.mp3"
            output.write_bytes(b"fake-audio")

            env = {
                "AZURE_SPEECH_KEY": "test-key",
                "AZURE_SPEECH_REGION": "eastus",
            }

            with patch.dict("os.environ", env, clear=True):
                with _patch_azure_modules(mock_speechsdk):
                    with patch("builtins.print"):
                        result = provider.synthesize_ssml(ssml, output)

        self.assertTrue(result)
        mock_speechsdk.SpeechConfig.assert_called_once_with(
            subscription="test-key",
            region="eastus",
        )
        mock_speechsdk.SpeechSynthesizer.assert_called_once()
        mock_synth.speak_ssml_async.assert_called_once_with(ssml)

    @patch.dict("os.environ", {}, clear=True)
    def test_synthesize_plain_text_without_credentials(self):
        provider = AzureTTSProvider()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "audio.mp3"
            with patch("builtins.print"):
                result = provider.synthesize(
                    "texto de teste",
                    output,
                    voice="pt-BR-AntonioNeural",
                )
            self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
