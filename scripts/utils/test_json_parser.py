"""Testes do JSON parser."""

import unittest

from scripts.utils.json_parser import parse_json


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


if __name__ == "__main__":
    unittest.main()
