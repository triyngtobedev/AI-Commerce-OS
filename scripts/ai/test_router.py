"""Testes do fallback Gemini → Groq → OpenRouter."""

import importlib
import os
import sys
import unittest
from unittest.mock import patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
router = importlib.import_module("scripts.ai.router")


class TestGeminiQuotaShared(unittest.TestCase):
    def setUp(self):
        from scripts.ai.gemini_quota import reset_gemini_metrics
        reset_gemini_metrics(reset_quota=True)

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-openrouter-key"})
    @patch.object(router, "openrouter_generate")
    @patch.object(router, "_groq_complete")
    @patch.object(router, "gemini_generate")
    def test_daily_quota_marks_shared_state(
        self, mock_gemini, mock_groq, mock_openrouter
    ):
        from scripts.ai.gemini_quota import is_gemini_quota_exhausted

        mock_gemini.side_effect = Exception("limit: 0 daily quota")
        mock_groq.return_value = "Resposta do Groq"
        mock_openrouter.return_value = "Resposta do OpenRouter"

        router.ask_ai("test prompt", "analysis")
        self.assertTrue(is_gemini_quota_exhausted())


class TestAiRouterFallback(unittest.TestCase):
    def setUp(self):
        from scripts.ai.gemini_quota import reset_gemini_metrics
        reset_gemini_metrics(reset_quota=True)
    @patch.object(router, "time")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-openrouter-key"})
    @patch.object(router, "openrouter_generate")
    @patch.object(router, "_groq_complete")
    @patch.object(router, "gemini_generate")
    def test_fallback_to_openrouter_when_gemini_and_groq_fail(
        self, mock_gemini, mock_groq, mock_openrouter, _mock_time
    ):
        mock_gemini.side_effect = Exception("Gemini quota exceeded")
        mock_groq.side_effect = Exception("Groq rate limit 429")
        mock_openrouter.return_value = "Resposta do OpenRouter"

        result = router.ask_ai("test prompt", "analysis")

        self.assertEqual(result, "Resposta do OpenRouter")
        mock_gemini.assert_called_once()
        self.assertEqual(mock_groq.call_count, 3)
        mock_openrouter.assert_called_once_with("test prompt")

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}, clear=False)
    @patch.object(router, "_groq_complete")
    @patch.object(router, "gemini_generate")
    def test_raises_when_all_providers_fail(self, mock_gemini, mock_groq):
        mock_gemini.side_effect = Exception("Gemini down")
        mock_groq.side_effect = Exception("Groq down")

        with self.assertRaises(Exception) as ctx:
            router.ask_ai("test prompt", "analysis")

        self.assertIn("Nenhuma API de IA disponível", str(ctx.exception))

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-openrouter-key"})
    @patch.object(router, "openrouter_generate")
    @patch.object(router, "_groq_complete")
    @patch.object(router, "gemini_generate")
    def test_gemini_success_skips_fallbacks(
        self, mock_gemini, mock_groq, mock_openrouter
    ):
        mock_gemini.return_value = "Resposta do Gemini"

        result = router.ask_ai("test prompt", "analysis")

        self.assertEqual(result, "Resposta do Gemini")
        mock_groq.assert_not_called()
        mock_openrouter.assert_not_called()


if __name__ == "__main__":
    unittest.main()
