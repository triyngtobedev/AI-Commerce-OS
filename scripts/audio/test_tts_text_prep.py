"""Testes para preparação de texto TTS."""

import unittest

from scripts.audio.tts_text_prep import prepare_text_for_tts


class TestTtsTextPrep(unittest.TestCase):

    def test_normalize_thousands(self):
        result = prepare_text_for_tts("devastou 2.000 quilômetros")
        self.assertIn("dois mil", result)

    def test_normalize_ranges(self):
        result = prepare_text_for_tts("energia de 10-15 megatons")
        self.assertIn("de 10 a 15", result)

    def test_preserves_content(self):
        text = "Em 1908, algo explodiu na Sibéria."
        result = prepare_text_for_tts(text)
        self.assertIn("1908", result)
        self.assertIn("Sibéria", result)

    def test_pause_marker_converted(self):
        result = prepare_text_for_tts("Algo aconteceu. [PAUSA] Ninguém esperava.")
        self.assertIn("... ...", result)
        self.assertNotIn("[PAUSA]", result)


if __name__ == "__main__":
    unittest.main()
