"""Testes do content generator."""

import sys
import unittest
from unittest.mock import patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from scripts.content.content_generator import generate_content


class TestContentGenerator(unittest.TestCase):
    @patch("scripts.content.content_generator.ask_ai")
    @patch("scripts.content.content_generator.load_cache", return_value=None)
    @patch("scripts.content.content_generator.save_cache")
    def test_generate_content_returns_dict(self, _save, _load, mock_ai):
        mock_ai.return_value = '{"texto_narracao": "Texto", "titulo": "T"}'

        produto = {"nome": "Mini Aspirador Portátil", "categoria": "Casa"}
        analise = {"score": 95, "potencial": "alto"}
        oportunidade = {"score_venda": 90, "decisao": "CRIAR_VIDEO"}
        roteiro = {"hook": "Hook", "problema": "Problema"}

        resultado = generate_content(produto, analise, oportunidade, roteiro)
        self.assertIsInstance(resultado, dict)


if __name__ == "__main__":
    unittest.main()
