"""Testes para Quality Checklist."""

import unittest

from scripts.core.production.quality_checklist import run_pre_render_checklist
from scripts.youtube.narration_utils import validate_hook_in_media_res, validate_wtf_moments


class TestQualityChecklist(unittest.TestCase):

    def _valid_dark5_script(self):
        return {
            "hook": "O corpo aparece às 3 da manhã. Ninguém ouve nada além do vento.",
            "contexto": "A cidade dorme. As luzes piscam. O silêncio pesa.",
            "fato_5": (
                "Número cinco: a porta estava trancada por dentro. "
                "[PAUSA] O cheiro de ferrugem invade o corredor. "
                "E isso não é o pior."
            ),
            "fato_4": (
                "Número quatro: três câmeras falharam juntas. "
                "[PAUSA] Ninguém sabe por quê. Mas o próximo número é pior."
            ),
            "fato_3": (
                "Número três: sangue seco no corrimão. "
                "[PAUSA] A temperatura cai de repente. Mas espere — tem mais."
            ),
            "fato_2": (
                "Número dois: um sussurro no rádio policial. "
                "[PAUSA] Ninguém responde. E agora, o número um."
            ),
            "fato_1": (
                "Número um: o cadáver não estava lá antes. "
                "[PAUSA] Impossível. Mas o verdadeiro impacto vem agora."
            ),
            "revelacao": "O detalhe muda tudo. A data bate com o desaparecimento.",
            "encerramento": "Se essa lista te pegou, inscreva-se no canal.",
        }

    def test_pre_render_passes_valid_script(self):
        report = run_pre_render_checklist(
            self._valid_dark5_script(),
            audio_duration=520.0,
        )
        self.assertTrue(report.passed)

    def test_pre_render_fails_generic_hook(self):
        script = self._valid_dark5_script()
        script["hook"] = "Hoje vamos falar sobre um mistério sinistro."
        report = run_pre_render_checklist(script, audio_duration=520.0)
        self.assertFalse(report.passed)
        self.assertTrue(any("hook_in_media_res" in f for f in report.failures))

    def test_validate_hook_in_media_res(self):
        warnings = validate_hook_in_media_res({
            "hook": "Neste vídeo veremos cinco fatos chocantes.",
        })
        self.assertEqual(len(warnings), 1)

    def test_validate_wtf_moments_requires_pause_or_shock(self):
        script = self._valid_dark5_script()
        script["fato_3"] = "Número três: algo estranho aconteceu naquela noite."
        warnings = validate_wtf_moments(script)
        self.assertTrue(any("fato_3" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
