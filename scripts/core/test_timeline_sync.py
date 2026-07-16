"""Testes para sincronização da Timeline com duração real do áudio."""

import unittest
from unittest.mock import patch

from scripts.core.emotional_timeline import build_emotional_timeline
from scripts.core.timeline_sync import (
    estimate_section_durations,
    sync_timeline_to_audio,
)


SCRIPT = {
    "sections": [
        {"text": "A explosão aconteceu em 1908.", "emotion": "mystery",
         "intensity": 0.4, "section_key": "hook"},
        {"text": "Ela destruiu milhões de árvores na Sibéria.", "emotion": "impact",
         "intensity": 0.9, "section_key": "contexto"},
        {"text": "O mistério permanece até hoje.", "emotion": "calm",
         "intensity": 0.3, "section_key": "encerramento"},
    ]
}


class TestTimelineSync(unittest.TestCase):

    @patch("scripts.core.timeline_sync.probe_duration")
    def test_sync_timeline_to_audio_updates_real_duration(self, mock_probe):
        mock_probe.return_value = 120.0
        timeline = build_emotional_timeline(SCRIPT)
        synced = sync_timeline_to_audio(timeline, "/fake/audio.mp3")

        self.assertAlmostEqual(synced.total_duration, 120.0, delta=0.5)
        total_real = sum(s.real_duration for s in synced.sections)
        self.assertAlmostEqual(total_real, 120.0, delta=0.5)
        self.assertTrue(synced.director_meta.get("synced_to_audio"))

    @patch("scripts.core.timeline_sync.probe_duration")
    def test_sync_sets_start_times(self, mock_probe):
        mock_probe.return_value = 90.0
        timeline = build_emotional_timeline(SCRIPT)
        synced = sync_timeline_to_audio(timeline, "/fake/audio.mp3")

        self.assertEqual(synced.sections[0].start_time, 0.0)
        for i in range(1, len(synced.sections)):
            prev = synced.sections[i - 1]
            curr = synced.sections[i]
            self.assertAlmostEqual(
                curr.start_time,
                prev.start_time + prev.real_duration,
                delta=0.5,
            )

    def test_estimate_section_durations(self):
        timeline = build_emotional_timeline(SCRIPT)
        durations = estimate_section_durations(timeline, 60.0)
        self.assertEqual(len(durations), 3)
        self.assertAlmostEqual(sum(durations), 60.0, delta=1.0)

    @patch("scripts.core.timeline_sync.probe_duration")
    def test_sync_with_fallback_duration(self, mock_probe):
        mock_probe.return_value = 0.0
        timeline = build_emotional_timeline(SCRIPT)
        synced = sync_timeline_to_audio(
            timeline,
            "/missing/audio.mp3",
            fallback_duration=45.0,
        )
        self.assertAlmostEqual(synced.total_duration, 45.0, delta=0.5)


if __name__ == "__main__":
    unittest.main()
