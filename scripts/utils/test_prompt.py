"""Testes do prompt loader."""

import unittest

from scripts.utils.prompt_loader import load_prompt


class TestPromptLoader(unittest.TestCase):
    def test_load_prompt_returns_string(self):
        prompt = load_prompt("product_analysis")
        self.assertIsInstance(prompt, str)
        self.assertTrue(len(prompt) > 0)


if __name__ == "__main__":
    unittest.main()
