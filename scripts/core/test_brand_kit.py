"""Testes rápidos para BrandKit e thumbnail (sem FFmpeg/render)."""

import tempfile
import unittest
from pathlib import Path

from scripts.core.brand_kit import (
    BrandKit,
    get_brand_kit,
    score_image_contrast,
    SCENE_MOTION,
)
from scripts.core.brand_engine import (
    get_brand_config,
    should_show_watermark,
    should_show_intro,
)
from scripts.youtube.thumbnail_generator import _derive_hook_text


class TestBrandKit(unittest.TestCase):

    def test_get_brand_kit_youtube_dark(self):
        kit = get_brand_kit("youtube_dark")
        self.assertEqual(kit.profile.channel_name, "Projeto Atlas")
        self.assertEqual(kit.colors.accent, (255, 183, 3))

    def test_wrap_hook_text_max_words(self):
        kit = get_brand_kit()
        lines = kit.wrap_hook_text("explosão de tunguska sibéria mistério")
        joined = " ".join(lines)
        self.assertLessEqual(len(joined.split()), 4)

    def test_wrap_hook_text_empty(self):
        kit = get_brand_kit()
        lines = kit.wrap_hook_text("")
        self.assertEqual(lines, ["DOCUMENTÁRIO"])

    def test_motion_by_scene_type(self):
        kit = get_brand_kit()
        self.assertEqual(kit.motion_for_scene("hook"), "zoom_in_center")
        self.assertEqual(kit.motion_for_scene("revelacao"), "zoom_in_center")
        self.assertIn(kit.motion_for_scene("unknown", 0), SCENE_MOTION.values())

    def test_crossfade_revelacao_longer(self):
        kit = get_brand_kit()
        default = kit.cinematic.crossfade_seconds
        revelacao = kit.crossfade_for_scene("revelacao")
        self.assertGreater(revelacao, default)

    def test_lower_third_only_hook_and_revelacao(self):
        kit = get_brand_kit()
        self.assertTrue(kit.should_show_lower_third("hook"))
        self.assertTrue(kit.should_show_lower_third("revelacao"))
        self.assertFalse(kit.should_show_lower_third("contexto"))

    def test_compose_thumbnail_creates_file(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow não instalado")

        kit = get_brand_kit()
        with tempfile.TemporaryDirectory() as tmp:
            hero = Path(tmp) / "hero.jpg"
            out = Path(tmp) / "thumb.jpg"
            Image.new("RGB", (1280, 720), color=(40, 60, 90)).save(hero, "JPEG")

            ok = kit.compose_thumbnail(hero, "TUNGUSKA", out, topic="O Mistério")
            self.assertTrue(ok)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 1000)

    def test_intro_outro_cards(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow não instalado")

        kit = get_brand_kit()
        with tempfile.TemporaryDirectory() as tmp:
            intro = Path(tmp) / "intro.jpg"
            outro = Path(tmp) / "outro.jpg"
            self.assertTrue(kit.render_intro_card(intro, topic="Tunguska"))
            self.assertTrue(kit.render_outro_card(outro))
            self.assertTrue(intro.exists())
            self.assertTrue(outro.exists())

    def test_score_image_contrast(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow não instalado")

        with tempfile.TemporaryDirectory() as tmp:
            high = Path(tmp) / "high.jpg"
            low = Path(tmp) / "low.jpg"
            Image.new("L", (320, 180), 255).save(high)
            img = Image.new("L", (320, 180), 128)
            for x in range(320):
                for y in range(180):
                    img.putpixel((x, y), (x + y) % 256)
            img.save(low)

            self.assertGreater(score_image_contrast(low), score_image_contrast(high))

    def test_watermark_filter_syntax(self):
        filt = get_brand_kit().watermark_filter()
        self.assertIn("drawtext", filt)
        self.assertIn("Projeto Atlas", filt)

    def test_lower_third_filter_syntax(self):
        filt = get_brand_kit().lower_third_filter("Sibéria 1908", 10.0)
        self.assertIn("drawtext", filt)
        self.assertIn("enable=", filt)


class TestBrandEngine(unittest.TestCase):

    def test_config_integrated_with_kit(self):
        config = get_brand_config("youtube_dark")
        self.assertIsInstance(config.kit, BrandKit)
        self.assertTrue(should_show_watermark())
        self.assertTrue(should_show_intro())

    def test_render_style_from_cinematic(self):
        config = get_brand_config()
        self.assertGreater(config.render.ken_burns_zoom_max, 1.0)
        self.assertIn("contrast", config.render.color_grade)


class TestThumbnailText(unittest.TestCase):

    def test_derive_hook_from_content(self):
        hook = _derive_hook_text({"thumbnail_texto": "Tunguska"}, None)
        self.assertEqual(hook, "Tunguska")

    def test_derive_hook_truncates_long_text(self):
        hook = _derive_hook_text(
            {"thumbnail_texto": "uma explosão misteriosa na sibéria"},
            None,
        )
        self.assertLessEqual(len(hook.split()), 4)

    def test_derive_hook_fallback_strategy(self):
        hook = _derive_hook_text({}, {"gancho": "O que aconteceu em 1908?"})
        self.assertTrue(len(hook) > 0)


if __name__ == "__main__":
    unittest.main()
