"""Testes de integração Timeline → SSML e Timeline → Scene Engine."""

import unittest

from scripts.audio.ssml_builder import build_ssml_from_sections
from scripts.core.emotional_timeline import build_emotional_timeline
from scripts.video.scene_emotion import apply_timeline_to_scenes


class TestTimelineSSMLIntegration(unittest.TestCase):

    def test_timeline_sections_produce_emotional_ssml(self):
        script = {
            "sections": [
                {"text": "A explosão aconteceu em 1908.", "emotion": "mystery", "intensity": 0.4},
                {"text": "Ela destruiu milhões de árvores.", "emotion": "impact", "intensity": 0.9},
            ]
        }
        timeline = build_emotional_timeline(script)
        ssml = build_ssml_from_sections(
            timeline.sections,
            voice="pt-BR-AntonioNeural",
            base_rate="-4%",
            base_pitch="-3Hz",
        )
        self.assertIn("mstts:express-as", ssml)
        self.assertIn('style="serious"', ssml)
        self.assertIn('style="excited"', ssml)
        self.assertIn("<break", ssml)


class TestTimelineSceneIntegration(unittest.TestCase):

    def test_apply_timeline_enriches_scenes(self):
        script = {
            "hook": "Em 1908 algo aconteceu.",
            "contexto": "A Sibéria era remota.",
            "desenvolvimento": "Testemunhas relataram.",
            "revelacao": "O mistério continua.",
            "consequencias": "Impacto global.",
            "encerramento": "Fim.",
        }
        timeline = build_emotional_timeline(script)
        scenes = {
            "cenas": [
                {"tipo": "hook", "visual": "explosion", "narracao": "Em 1908."},
                {"tipo": "contexto", "visual": "siberia", "narracao": "Remota."},
            ]
        }
        enriched = apply_timeline_to_scenes(scenes, timeline)
        hook_scene = enriched["cenas"][0]
        self.assertIn("emotion", hook_scene)
        self.assertIn("intensity", hook_scene)
        self.assertIn("visual_intent", hook_scene)
        self.assertIn("timeline", hook_scene)
        self.assertIn("scene_motion", hook_scene)
        self.assertEqual(hook_scene["emotion"], "impact")

    def test_emotional_timeline_attached_to_scenes(self):
        script = {"sections": [{"text": "Teste.", "emotion": "calm", "intensity": 0.3}]}
        timeline = build_emotional_timeline(script)
        scenes = {"cenas": [{"tipo": "hook", "visual": "test"}]}
        enriched = apply_timeline_to_scenes(scenes, timeline)
        self.assertIn("emotional_timeline", enriched)


if __name__ == "__main__":
    unittest.main()
