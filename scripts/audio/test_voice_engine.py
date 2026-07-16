"""Testes para Voice Engine e narração aprimorada."""

import unittest

from scripts.audio.voice_engine import VoiceEngine, VOICE_PRESETS
from scripts.youtube.narration_utils import (
    clean_script_phrases,
    detect_banned_phrases,
    stitch_script_to_narration,
)


class TestVoiceEngine(unittest.TestCase):

    def test_resolve_documentary_preset(self):
        engine = VoiceEngine(providers=[])
        preset = engine.resolve_preset("documentario_narrado")
        self.assertEqual(preset["voice"], "pt-BR-AntonioNeural")
        self.assertIn("rate", preset)

    def test_misterio_preset_slower(self):
        engine = VoiceEngine(providers=[])
        mystery = engine.resolve_preset("misterio_nao_resolvido")
        self.assertEqual(
            mystery["voice"],
            VOICE_PRESETS["misterio_nao_resolvido"]["voice"],
        )
        self.assertTrue(mystery["rate"].startswith("-"))


class TestScriptCleaning(unittest.TestCase):

    def test_clean_imagine_uma(self):
        script = {
            "hook": "Imagine uma explosão devastadora na Sibéria.",
            "contexto": "Em 1908 algo aconteceu.",
        }
        cleaned = clean_script_phrases(script)
        self.assertNotIn("Imagine uma", cleaned["hook"])

    def test_detect_banned_phrases(self):
        script = {
            "encerramento": "Junte-se a nós na exploração do desconhecido.",
        }
        found = detect_banned_phrases(script)
        self.assertTrue(len(found) > 0)

    def test_transitions_optional(self):
        script = {
            "hook": "Primeira frase.",
            "contexto": "Segunda seção.",
            "desenvolvimento": "",
            "revelacao": "",
            "consequencias": "",
            "encerramento": "",
        }
        without = stitch_script_to_narration(script, use_transitions=False)
        with_t = stitch_script_to_narration(script, use_transitions=True)
        self.assertEqual(without, "Primeira frase. Segunda seção.")
        self.assertIn("voltar no tempo", with_t)


if __name__ == "__main__":
    unittest.main()
