"""Testes para EmotionMapper."""

import unittest

from scripts.audio.emotion_mapper import EmotionMapper, get_emotion_mapper


class TestEmotionMapper(unittest.TestCase):

    def test_mystery_maps_to_serious(self):
        mapper = get_emotion_mapper()
        self.assertEqual(mapper.azure_express_as("mystery"), "serious")

    def test_impact_maps_to_excited(self):
        mapper = get_emotion_mapper()
        self.assertEqual(mapper.azure_express_as("impact"), "excited")

    def test_sad_maps_to_sad(self):
        mapper = get_emotion_mapper()
        self.assertEqual(mapper.azure_express_as("sad"), "sad")

    def test_calm_maps_to_calm(self):
        mapper = get_emotion_mapper()
        self.assertEqual(mapper.azure_express_as("calm"), "calm")

    def test_warning_maps_to_fearful(self):
        mapper = get_emotion_mapper()
        self.assertEqual(mapper.azure_express_as("warning"), "fearful")

    def test_unknown_emotion_falls_back_to_calm(self):
        mapper = get_emotion_mapper()
        self.assertEqual(mapper.azure_express_as("unknown_xyz"), "calm")

    def test_intensity_affects_zoom(self):
        mapper = get_emotion_mapper()
        low = mapper.zoom_intensity("impact", 0.2)
        high = mapper.zoom_intensity("impact", 0.9)
        self.assertGreater(high, low)

    def test_scene_motion_by_emotion(self):
        mapper = EmotionMapper()
        self.assertEqual(mapper.scene_motion("mystery"), "zoom_in_center")
        self.assertEqual(mapper.transition_speed("impact"), "fast")
        self.assertEqual(mapper.transition_speed("calm"), "normal")


if __name__ == "__main__":
    unittest.main()
