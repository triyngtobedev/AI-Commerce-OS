"""Testes para Visual Intent Engine."""

import unittest

from scripts.core.emotional_timeline import TimelineSection, build_emotional_timeline
from scripts.core.visual_intent_engine import (
    VisualIntentSpec,
    apply_visual_intents,
    build_visual_search_query,
    resolve_visual_intent,
)


class TestVisualIntentEngine(unittest.TestCase):

    def test_resolve_visual_intent_for_mystery(self):
        section = TimelineSection(
            text="Ruínas antigas.",
            emotion="mystery",
            intensity=0.7,
            visual_intent="ancient_ruins",
            camera_motion="slow_push",
        )
        spec = resolve_visual_intent(section)
        self.assertIsInstance(spec, VisualIntentSpec)
        self.assertEqual(spec.visual_intent, "ancient_ruins")
        self.assertIn("historical_photo", spec.asset_priority)
        self.assertEqual(spec.color_palette, "cold")

    def test_resolve_defaults_for_unknown_intent(self):
        spec = resolve_visual_intent({
            "visual_intent": "unknown_intent",
            "emotion": "calm",
            "camera_motion": "slow_pan",
        })
        self.assertEqual(spec.visual_intent, "unknown_intent")
        self.assertGreater(len(spec.asset_priority), 0)

    def test_apply_visual_intents_to_timeline(self):
        script = {
            "sections": [
                {"text": "Hook.", "emotion": "impact", "intensity": 0.9,
                 "section_key": "hook", "visual_intent": "dramatic_opening"},
            ]
        }
        timeline = build_emotional_timeline(script)
        enriched = apply_visual_intents(timeline)
        self.assertTrue(enriched.director_meta.get("visual_intents_applied"))

    def test_build_visual_search_query(self):
        section = TimelineSection(
            text="Tunguska",
            emotion="mystery",
            intensity=0.5,
            visual_intent="ancient_ruins",
        )
        query = build_visual_search_query("Tunguska explosion", section)
        self.assertIn("Tunguska", query)
        self.assertIn("ancient", query.lower())

    def test_camera_alias_mapping(self):
        spec = resolve_visual_intent({
            "visual_intent": "general_narrative",
            "emotion": "calm",
            "camera_motion": "slow_push",
        })
        self.assertEqual(spec.camera, "zoom_in_center")


if __name__ == "__main__":
    unittest.main()
