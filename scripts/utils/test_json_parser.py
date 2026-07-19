"""Testes do JSON parser."""

import unittest

from scripts.utils.json_parser import parse_json, safe_parse_json


class TestJsonParser(unittest.TestCase):
    def test_parse_json_from_markdown_block(self):
        resposta_ia = """
```json
{
  "score": 92,
  "potencial": "alto"
}
```
"""
        resultado = parse_json(resposta_ia)
        self.assertEqual(resultado["score"], 92)
        self.assertEqual(resultado["potencial"], "alto")

    def test_safe_parse_json_extracts_object_from_mixed_text(self):
        resposta = 'Análise:\n{"score": 71, "potencial": "medio"}\nFim.'
        resultado = safe_parse_json(resposta)
        self.assertEqual(resultado["score"], 71)

    def test_safe_parse_json_returns_none_for_invalid(self):
        self.assertIsNone(safe_parse_json("não é json"))
        self.assertIsNone(safe_parse_json(""))
        self.assertIsNone(safe_parse_json(None))

    def test_parse_json_raises_for_invalid(self):
        with self.assertRaises(ValueError):
            parse_json("não é json")


if __name__ == "__main__":
    unittest.main()
