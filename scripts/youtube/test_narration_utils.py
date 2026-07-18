"""Testes para validação de narração dark."""

import unittest

from scripts.youtube.narration_utils import (
    validate_sentence_length,
    validate_scene_hooks,
    strip_pause_markers,
    MAX_WORDS_PER_SENTENCE,
)


class TestNarrationDarkRules(unittest.TestCase):

    def test_detects_long_sentences(self):
        script = {
            "hook": (
                "Esta frase tem mais de doze palavras e deveria "
                "ser detectada como violação do limite máximo permitido."
            ),
        }
        warnings = validate_sentence_length(script)
        self.assertTrue(any("hook" in w for w in warnings))

    def test_accepts_short_sentences(self):
        script = {
            "hook": "Em 1908, algo explodiu. Ninguém sabe o que foi.",
        }
        warnings = validate_sentence_length(script)
        self.assertEqual(warnings, [])

    def test_detects_missing_hooks(self):
        script = {
            "hook": "Fato surpreendente sobre emus.",
            "contexto": "A Austrália enfrentou uma guerra estranha.",
            "encerramento": "Inscreva-se no canal.",
        }
        warnings = validate_scene_hooks(script)
        self.assertTrue(len(warnings) >= 1)

    def test_strip_pause_markers(self):
        text = "Algo aconteceu. [PAUSA] Ninguém esperava."
        result = strip_pause_markers(text)
        self.assertNotIn("[PAUSA]", result)
        self.assertIn("aconteceu", result)

    def test_max_words_constant(self):
        self.assertEqual(MAX_WORDS_PER_SENTENCE, 12)


if __name__ == "__main__":
    unittest.main()
