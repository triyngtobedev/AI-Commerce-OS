"""Testes do gerador de cenas YouTube."""

import unittest

from scripts.youtube.youtube_scenes import (
    DARK5_SCENE_TYPES,
    SCENE_TYPES,
    generate_youtube_scenes,
)


class TestYoutubeScenes(unittest.TestCase):

    def test_documentario_scene_types(self):
        topic = {"nome": "Tunguska", "keywords": ["explosão"]}
        content = {"texto_narracao": " ".join(["palavra"] * 80)}
        strategy = {"roteiro_template": "documentario"}

        result = generate_youtube_scenes(topic, content, strategy)
        types = [scene["tipo"] for scene in result["cenas"]]

        self.assertEqual(types, SCENE_TYPES)
        self.assertEqual(len(types), 8)

    def test_dark5_scene_types(self):
        topic = {"nome": "Alexandria", "keywords": ["biblioteca"]}
        content = {"texto_narracao": " ".join(["palavra"] * 90)}
        strategy = {"roteiro_template": "dark5"}

        result = generate_youtube_scenes(topic, content, strategy)
        types = [scene["tipo"] for scene in result["cenas"]]

        self.assertEqual(types, DARK5_SCENE_TYPES)
        self.assertIn("fato_5", types)
        self.assertIn("fato_1", types)
        self.assertNotIn("desenvolvimento_1", types)


if __name__ == "__main__":
    unittest.main()
