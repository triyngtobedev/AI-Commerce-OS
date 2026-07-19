"""Testes para Script Parser."""

import unittest

from scripts.creative.script_parser import (
    enrich_script_with_emotions,
    extract_section_text,
    parse_script_sections,
    sync_script_from_keyed_sections,
)


class TestScriptParser(unittest.TestCase):

    def test_parses_emotional_format(self):
        script = {
            "sections": [
                {
                    "text": "A explosão aconteceu em 1908.",
                    "emotion": "mystery",
                    "intensity": 0.4,
                    "visual_intent": "ancient_ruins",
                    "camera_motion": "slow_push",
                },
                {"text": "Ela destruiu milhões de árvores.", "emotion": "impact", "intensity": 0.9},
            ]
        }
        parsed = parse_script_sections(script)
        self.assertEqual(parsed["format"], "emotional")
        self.assertEqual(len(parsed["sections"]), 2)
        self.assertEqual(parsed["sections"][0]["visual_intent"], "ancient_ruins")
        self.assertEqual(parsed["sections"][0]["camera_motion"], "slow_push")

    def test_converts_legacy_youtube_format(self):
        script = {
            "hook": "Em 1908 algo aconteceu.",
            "contexto": "A Sibéria era remota.",
            "desenvolvimento": "",
            "revelacao": "O mistério continua.",
            "consequencias": "",
            "encerramento": "Fim.",
        }
        parsed = parse_script_sections(script)
        self.assertEqual(parsed["format"], "legacy_youtube")
        self.assertGreaterEqual(len(parsed["sections"]), 3)
        self.assertEqual(parsed["sections"][0]["section_key"], "hook")
        self.assertIn("emotion", parsed["sections"][0])
        self.assertIn("visual_intent", parsed["sections"][0])
        self.assertIn("camera_motion", parsed["sections"][0])

    def test_converts_legacy_tiktok_format(self):
        script = {
            "gancho": "Você precisa ver isso.",
            "roteiro": "Apresentação do produto.",
        }
        parsed = parse_script_sections(script)
        self.assertEqual(parsed["format"], "legacy_tiktok")
        self.assertEqual(len(parsed["sections"]), 2)

    def test_enrich_preserves_original_keys(self):
        script = {"hook": "Teste.", "contexto": "Mais texto."}
        enriched = enrich_script_with_emotions(script)
        self.assertIn("hook", enriched)
        self.assertIn("sections", enriched)
        self.assertEqual(enriched["hook"], "Teste.")

    def test_plain_string_input(self):
        parsed = parse_script_sections("Texto simples.")
        self.assertEqual(len(parsed["sections"]), 1)
        self.assertEqual(parsed["format"], "plain")

    def test_empty_script(self):
        parsed = parse_script_sections({})
        self.assertEqual(parsed["sections"], [])

    def test_extract_section_text_prefers_narracao(self):
        self.assertEqual(
            extract_section_text({"narracao": "Texto narrado."}),
            "Texto narrado.",
        )

    def test_sync_script_from_keyed_sections_rebuilds_sections(self):
        script = {
            "hook": {"text": " ".join(["hook"] * 50)},
            "contexto": {"text": " ".join(["contexto"] * 200)},
            "desenvolvimento": {"text": " ".join(["dev"] * 300)},
            "sections": [{"text": "stale short", "section_key": "hook"}],
        }
        synced = sync_script_from_keyed_sections(script)
        self.assertGreater(len(synced["sections"]), 1)
        full = " ".join(section["text"] for section in synced["sections"])
        self.assertGreater(len(full.split()), 500)


if __name__ == "__main__":
    unittest.main()
