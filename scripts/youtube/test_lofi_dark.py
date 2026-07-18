"""Testes do template lofi_dark."""

import unittest

from scripts.youtube.lofi_dark_config import (
    LOFI_BACKGROUND_QUERIES,
    LOFI_DARK_SCRIPT_SECTIONS,
    LOFI_DARK_TARGET_DURATION_SECONDS,
    is_lofi_dark,
    lofi_background_query,
)
from scripts.youtube.narration_utils import _script_sections_for


class TestLofiDarkConfig(unittest.TestCase):

    def test_is_lofi_dark(self):
        self.assertTrue(is_lofi_dark("lofi_dark"))
        self.assertFalse(is_lofi_dark("documentario"))
        self.assertFalse(is_lofi_dark("dark5"))

    def test_background_queries_rotate(self):
        self.assertEqual(len(LOFI_BACKGROUND_QUERIES), 10)
        self.assertEqual(lofi_background_query(0), LOFI_BACKGROUND_QUERIES[0])
        self.assertEqual(lofi_background_query(10), LOFI_BACKGROUND_QUERIES[0])

    def test_script_sections_detection(self):
        script = {"hook": "a", "reflexao_1": "b", "encerramento": "c"}
        sections = _script_sections_for(script)
        self.assertEqual(sections, LOFI_DARK_SCRIPT_SECTIONS)

    def test_target_duration(self):
        self.assertEqual(LOFI_DARK_TARGET_DURATION_SECONDS, 1200)


if __name__ == "__main__":
    unittest.main()
