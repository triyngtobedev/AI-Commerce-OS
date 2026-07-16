"""Testes para SSML builder (sem chamadas de rede)."""

import unittest
import xml.etree.ElementTree as ET

from scripts.audio.ssml_builder import build_ssml, escape_ssml


SAMPLE_YOUTUBE_SCRIPT = {
    "hook": "Em 1908, algo devastou a Sibéria.",
    "contexto": "A região era remota e pouco habitada.",
    "desenvolvimento": "Testemunhas relataram um clarão no céu.",
    "revelacao": "Ninguém encontrou o cratera por décadas.",
    "consequencias": "Cientistas debatem até hoje.",
    "encerramento": "O mistério permanece.",
}


class TestSSMLBuilder(unittest.TestCase):

    def test_build_ssml_is_valid_xml(self):
        ssml = build_ssml(
            SAMPLE_YOUTUBE_SCRIPT,
            voice="pt-BR-AntonioNeural",
            base_rate="-4%",
            base_pitch="-3Hz",
        )
        self.assertTrue(ssml)
        root = ET.fromstring(ssml)
        self.assertTrue(root.tag.endswith("speak"))

    def test_build_ssml_contains_break_and_prosody(self):
        ssml = build_ssml(
            SAMPLE_YOUTUBE_SCRIPT,
            voice="pt-BR-AntonioNeural",
            base_rate="-4%",
            base_pitch="-3Hz",
        )
        self.assertIn("<break", ssml)
        self.assertIn("<prosody", ssml)
        self.assertIn("mstts:express-as", ssml)

    def test_escape_ssml_special_characters(self):
        escaped = escape_ssml("A & B <tag> > fim")
        self.assertEqual(escaped, "A &amp; B &lt;tag&gt; &gt; fim")

    def test_build_ssml_escapes_input_characters(self):
        script = {
            "hook": "Empresa X & Y <teste> confirmou 100 casos.",
            "contexto": "",
            "desenvolvimento": "",
            "revelacao": "",
            "consequencias": "",
            "encerramento": "",
        }
        ssml = build_ssml(
            script,
            voice="pt-BR-AntonioNeural",
            base_rate="-4%",
            base_pitch="-3Hz",
        )
        self.assertIn("&amp;", ssml)
        self.assertIn("&lt;teste&gt;", ssml)
        ET.fromstring(ssml)

    def test_build_ssml_emphasis_on_numbers(self):
        ssml = build_ssml(
            {"hook": "Em 1908 houve 3 explosões.", "contexto": "", "desenvolvimento": "",
             "revelacao": "", "consequencias": "", "encerramento": ""},
            voice="pt-BR-AntonioNeural",
            base_rate="-4%",
            base_pitch="-3Hz",
        )
        self.assertIn("<emphasis", ssml)


if __name__ == "__main__":
    unittest.main()
