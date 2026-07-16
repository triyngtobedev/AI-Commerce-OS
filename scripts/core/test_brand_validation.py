"""Testes para validação centralizada de brand assets."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.core.brand_validation import validate_brand_asset


class TestBrandValidation(unittest.TestCase):

    def test_missing_file_invalid(self):
        report = validate_brand_asset(Path("/nonexistent/file.png"))
        self.assertFalse(report.valid)
        self.assertFalse(report.exists)

    def test_valid_rgb_image(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.jpg"
            img = Image.new("RGB", (100, 100))
            pixels = img.load()
            for x in range(100):
                for y in range(100):
                    pixels[x, y] = (x * 2, y * 2, 30)
            img.save(path)

            report = validate_brand_asset(path, asset_type="image")
            self.assertTrue(report.valid)
            self.assertEqual(report.width, 100)


if __name__ == "__main__":
    unittest.main()
