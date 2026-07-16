"""Testes para Director Engine — mocks apenas, sem APIs."""

import unittest

from scripts.core.director_engine import (
    DirectorDecision,
    direct_script,
    get_director_decision,
)


YOUTUBE_SCRIPT = {
    "hook": "A explosão aconteceu em 1908.",
    "contexto": "A Sibéria era remota.",
    "desenvolvimento": "Testemunhas viram um clarão.",
    "revelacao": "Ninguém encontrou o cratera.",
    "consequencias": "Cientistas debatem até hoje.",
    "encerramento": "O mistério permanece.",
}


class TestDirectorEngine(unittest.TestCase):

    def test_direct_script_enriches_sections(self):
        directed, decision = direct_script(YOUTUBE_SCRIPT)
        self.assertIn("sections", directed)
        self.assertIn("_director", directed)
        self.assertGreater(len(directed["sections"]), 0)

    def test_director_decision_has_climax(self):
        _, decision = direct_script(YOUTUBE_SCRIPT)
        self.assertIn(decision.climax_section, {"revelacao", "impacto", "resultado", "desenvolvimento"})
        self.assertGreater(len(decision.intensity_curve), 0)

    def test_director_applies_silence_moments(self):
        directed, decision = direct_script(
            YOUTUBE_SCRIPT,
            strategy={"angulo": "misterio_nao_resolvido"},
        )
        self.assertIn("revelacao", decision.silence_moments)
        reveal = next(
            s for s in directed["sections"]
            if s.get("section_key") == "revelacao"
        )
        self.assertGreaterEqual(reveal.get("pause_before", 0), 0.3)

    def test_director_rhythm_from_strategy(self):
        _, decision = direct_script(
            YOUTUBE_SCRIPT,
            strategy={"angulo": "fato_surpreendente"},
        )
        self.assertEqual(decision.rhythm, "fast")

    def test_get_director_decision_from_script(self):
        directed, _ = direct_script(YOUTUBE_SCRIPT)
        recovered = get_director_decision(directed)
        self.assertIsNotNone(recovered)
        self.assertIsInstance(recovered, DirectorDecision)

    def test_legacy_keys_preserved(self):
        directed, _ = direct_script(YOUTUBE_SCRIPT)
        self.assertIn("hook", directed)
        self.assertIn("revelacao", directed)


if __name__ == "__main__":
    unittest.main()
