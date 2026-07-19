"""Testes do fallback Groq → OpenRouter."""

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


class TestAiRouterFallback(unittest.TestCase):
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-openrouter-key"})
    @patch.object(router, "openrouter_generate")
    @patch.object(router, "_groq_complete")
    def test_fallback_to_openrouter_when_groq_fails(
        self, mock_groq, mock_openrouter
    ):
        mock_groq.side_effect = Exception("Groq rate limit 429")
        mock_openrouter.return_value = "Resposta do OpenRouter"

        result = router.ask_ai("test prompt", "analysis")

        self.assertEqual(result, "Resposta do OpenRouter")
        mock_groq.assert_called_once_with("test prompt", "llama-3.1-8b-instant", "analysis")
        mock_openrouter.assert_called_once_with("test prompt", model=router.OPENROUTER_MODEL)

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}, clear=False)
    @patch.object(router, "_groq_complete")
    def test_raises_when_all_providers_fail(self, mock_groq):
        mock_groq.side_effect = Exception("Groq down")

        with self.assertRaises(Exception) as ctx:
            router.ask_ai("test prompt", "analysis")

        self.assertIn("Nenhuma API de IA disponível", str(ctx.exception))

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-openrouter-key"})
    @patch.object(router, "openrouter_generate")
    @patch.object(router, "_groq_complete")
    def test_groq_success_skips_openrouter(self, mock_groq, mock_openrouter):
        mock_groq.return_value = "Resposta do Groq"

        result = router.ask_ai("test prompt", "analysis")

        self.assertEqual(result, "Resposta do Groq")
        mock_openrouter.assert_not_called()

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-openrouter-key"})
    @patch.object(router, "openrouter_generate")
    @patch.object(router, "_groq_complete")
    def test_script_generation_tries_both_groq_models(self, mock_groq, mock_openrouter):
        mock_groq.side_effect = [
            Exception("Groq rate limit 429"),
            "Resposta do Groq 70B",
        ]

        result = router.ask_ai("test prompt", "script_generation")

        self.assertEqual(result, "Resposta do Groq 70B")
        self.assertEqual(mock_groq.call_count, 2)
        mock_openrouter.assert_not_called()


if __name__ == "__main__":
    unittest.main()
