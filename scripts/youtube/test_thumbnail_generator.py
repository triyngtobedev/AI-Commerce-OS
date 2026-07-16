"""Testes para thumbnail generator — caminho sem hero image."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.youtube.thumbnail_generator import generate_thumbnail


class TestThumbnailGeneratorFallback(unittest.TestCase):

    def test_generates_thumbnail_without_hero_image(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow não instalado")

        subject = {"nome": "Tunguska"}
        content = {
            "titulo": "O Mistério de Tunguska",
            "thumbnail_texto": "EXPLOSÃO SIBÉRIA",
        }

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)

            with patch(
                "scripts.youtube.thumbnail_generator.content_output_dir",
                return_value=folder,
            ), patch(
                "scripts.youtube.thumbnail_generator._pick_best_hero_image",
                return_value=None,
            ), patch("builtins.print"):
                result = generate_thumbnail(
                    subject,
                    content,
                    platform="youtube_dark",
                )

            self.assertIsNotNone(result)
            thumb = Path(result)
            self.assertTrue(thumb.exists())
            self.assertGreater(thumb.stat().st_size, 1000)

            with Image.open(thumb) as img:
                self.assertEqual(img.size, (1280, 720))
                pixels = list(img.getdata())
                unique = len(set(pixels[:500]))
                self.assertGreater(unique, 1)


if __name__ == "__main__":
    unittest.main()
