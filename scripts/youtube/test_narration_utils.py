"""Testes para utilitários de narração YouTube."""

import unittest

from scripts.youtube.narration_utils import (
    stitch_script_to_narration,
    count_words,
    estimate_duration_seconds,
    validate_narration,
    MIN_NARRATION_WORDS,
    TARGET_NARRATION_WORDS,
)


SAMPLE_SCRIPT = {
    "hook": "Em 1908, algo explodiu na Sibéria com força devastadora.",
    "contexto": "A Rússia vivia uma era de transformação científica e industrial.",
    "desenvolvimento": " " * 400 + "fatos " * 100,
    "revelacao": "Ninguém encontrou um cráter de impacto.",
    "consequencias": "O evento mudou como a ciência vê ameaças cósmicas.",
    "encerramento": "Inscreva-se para mais mistérios históricos.",
}


class TestNarrationUtils(unittest.TestCase):

    def test_stitch_preserves_all_sections(self):
        narration = stitch_script_to_narration(SAMPLE_SCRIPT)
        self.assertIn("1908", narration)
        self.assertIn("cráter", narration)
        self.assertIn("Inscreva-se", narration)

    def test_stitch_does_not_summarize(self):
        script = {
            "hook": "Primeira frase completa do hook.",
            "contexto": "Segunda seção com detalhes importantes.",
            "desenvolvimento": "",
            "revelacao": "",
            "consequencias": "",
            "encerramento": "",
        }
        narration = stitch_script_to_narration(script)
        self.assertEqual(
            narration,
            "Primeira frase completa do hook. Segunda seção com detalhes importantes.",
        )

    def test_count_words(self):
        self.assertEqual(count_words("uma duas três"), 3)

    def test_estimate_duration(self):
        text = " ".join(["palavra"] * 150)
        seconds = estimate_duration_seconds(text)
        self.assertEqual(seconds, 60)

    def test_validate_short_narration_warns(self):
        warnings = validate_narration("texto curto demais")
        self.assertTrue(len(warnings) > 0)

    def test_validate_long_narration_ok(self):
        text = " ".join(["palavra"] * TARGET_NARRATION_WORDS)
        warnings = validate_narration(text)
        self.assertEqual(len(warnings), 0)


if __name__ == "__main__":
    unittest.main()
