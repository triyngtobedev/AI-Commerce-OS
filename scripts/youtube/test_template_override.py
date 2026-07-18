"""Testes de override de template via env."""

import os
import unittest
from unittest.mock import patch

from scripts.youtube.template_override import (
    apply_template_override,
    requested_roteiro_template,
)


class TestTemplateOverride(unittest.TestCase):

    def test_requested_from_env(self):
        with patch.dict(os.environ, {"PIPELINE_ROTEIRO_TEMPLATE": "lofi_dark"}):
            self.assertEqual(requested_roteiro_template(), "lofi_dark")

    def test_apply_lofi_dark(self):
        with patch.dict(os.environ, {"PIPELINE_ROTEIRO_TEMPLATE": "lofi_dark"}):
            result = apply_template_override({"roteiro_template": "documentario"})
        self.assertEqual(result["roteiro_template"], "lofi_dark")
        self.assertEqual(result["duracao_alvo"], "20 minutos")

    def test_no_env_passthrough(self):
        with patch.dict(os.environ, {}, clear=True):
            original = {"roteiro_template": "documentario", "duracao_alvo": "8 minutos"}
            self.assertEqual(apply_template_override(original), original)


if __name__ == "__main__":
    unittest.main()
