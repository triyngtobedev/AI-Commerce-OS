"""Testes para EmotionalTimeline."""

import unittest

from scripts.core.emotional_timeline import (
    EmotionalTimeline,
    build_emotional_timeline,
)


YOUTUBE_SCRIPT = {
    "hook": "A explosão aconteceu em 1908.",
    "contexto": "A Sibéria era remota.",
    "desenvolvimento": "Testemunhas viram um clarão.",
    "revelacao": "Ninguém encontrou o cratera.",
    "consequencias": "Cientistas debatem até hoje.",
    "encerramento": "O mistério permanece.",
}

EMOTIONAL_SCRIPT = {
    "sections": [
        {"text": "A explosão aconteceu em 1908.", "emotion": "mystery", "intensity": 0.4},
        {"text": "Ela destruiu milhões de árvores.", "emotion": "impact", "intensity": 0.9},
    ]
}


class TestEmotionalTimeline(unittest.TestCase):

    def test_from_legacy_youtube_script(self):
        timeline = build_emotional_timeline(YOUTUBE_SCRIPT)
        self.assertEqual(len(timeline.sections), 6)
        self.assertEqual(timeline.sections[0].emotion, "impact")
        self.assertGreater(timeline.total_duration, 0)

    def test_from_emotional_script(self):
        timeline = build_emotional_timeline(EMOTIONAL_SCRIPT)
        self.assertEqual(len(timeline.sections), 2)
        self.assertEqual(timeline.sections[1].emotion, "impact")
        self.assertAlmostEqual(timeline.sections[1].intensity, 0.9)

    def test_scales_to_audio_duration(self):
        timeline = build_emotional_timeline(EMOTIONAL_SCRIPT, audio_duration=120.0)
        total = sum(s.duration for s in timeline.sections)
        self.assertAlmostEqual(total, 120.0, delta=1.0)

    def test_to_dict_roundtrip(self):
        timeline = build_emotional_timeline(EMOTIONAL_SCRIPT)
        restored = EmotionalTimeline.from_dict(timeline.to_dict())
        self.assertEqual(len(restored.sections), 2)
        self.assertEqual(restored.sections[0].text, timeline.sections[0].text)

    def test_sections_have_scene_weight(self):
        timeline = build_emotional_timeline(YOUTUBE_SCRIPT)
        hook = timeline.sections[0]
        self.assertEqual(hook.section_key, "hook")
        self.assertGreater(hook.scene_weight, 0)

    def test_sections_have_visual_intent(self):
        timeline = build_emotional_timeline(YOUTUBE_SCRIPT)
        for section in timeline.sections:
            self.assertTrue(section.visual_intent)
            self.assertTrue(section.camera_motion)
            self.assertGreater(section.estimated_duration, 0)

    def test_emotional_script_has_transition_hint(self):
        timeline = build_emotional_timeline(EMOTIONAL_SCRIPT)
        self.assertEqual(timeline.sections[0].transition_hint, "fade_slow")


class TestScriptToTimelineIntegration(unittest.TestCase):

    def test_script_produces_timeline_with_pauses(self):
        timeline = build_emotional_timeline(EMOTIONAL_SCRIPT)
        for section in timeline.sections:
            self.assertGreaterEqual(section.pause_before, 0)
            self.assertGreaterEqual(section.pause_after, 0)


if __name__ == "__main__":
    unittest.main()
