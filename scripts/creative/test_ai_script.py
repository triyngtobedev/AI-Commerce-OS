"""Testes do AI script generator."""

import sys
import unittest
from unittest.mock import patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from scripts.creative.ai_script_generator import generate_ai_script


class TestAiScriptGenerator(unittest.TestCase):
    @patch("scripts.creative.ai_script_generator.ask_ai")
    @patch("scripts.creative.ai_script_generator.load_cache", return_value=None)
    @patch("scripts.creative.ai_script_generator.save_cache")
    def test_generate_ai_script_returns_dict(self, _save, _load, mock_ai):
        mock_ai.return_value = '{"hook": "Test hook", "problema": "Test"}'

        produto = {"nome": "Mini Aspirador Portátil", "categoria": "Casa"}
        analise = {"score": 95, "publico_alvo": "Público teste"}
        oportunidade = {"score_venda": 90}

        resultado = generate_ai_script(produto, analise, oportunidade)
        self.assertIsInstance(resultado, dict)


if __name__ == "__main__":
    unittest.main()
