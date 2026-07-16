"""
Testes da configuração de publicação YouTube.
"""

import os
import unittest
from unittest.mock import patch

from scripts.publisher.youtube_publish_config import (
    resolve_upload_settings,
    resolve_upload_visibility,
)


class TestResolveUploadVisibility(unittest.TestCase):

    def test_defaults_to_private(self):
        with patch.dict(os.environ, {}, clear=True):
            visibility, ctx = resolve_upload_visibility()

        self.assertEqual(visibility, "private")
        self.assertIn("private", ctx["reason"])

    def test_env_visibility(self):
        with patch.dict(
            os.environ,
            {"UPLOAD_VISIBILITY": "unlisted"},
            clear=True,
        ):
            visibility, ctx = resolve_upload_visibility()

        self.assertEqual(visibility, "unlisted")
        self.assertIn("UPLOAD_VISIBILITY", ctx["reason"])

    def test_cli_overrides_env(self):
        with patch.dict(
            os.environ,
            {"UPLOAD_VISIBILITY": "public"},
            clear=True,
        ):
            visibility, _ = resolve_upload_visibility(cli_privacy="unlisted")

        self.assertEqual(visibility, "unlisted")

    def test_invalid_env_falls_back_to_private(self):
        with patch.dict(
            os.environ,
            {"UPLOAD_VISIBILITY": "invalid"},
            clear=True,
        ):
            visibility, ctx = resolve_upload_visibility()

        self.assertEqual(visibility, "private")
        self.assertIn("inválido", ctx["reason"])


class TestResolveUploadSettings(unittest.TestCase):

    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            enabled, ctx = resolve_upload_settings(
                cli_upload=False,
            )

        self.assertFalse(enabled)
        self.assertEqual(ctx["decision"], "disabled")

    def test_cli_upload_enables(self):
        with patch.dict(os.environ, {}, clear=True):
            enabled, ctx = resolve_upload_settings(
                cli_upload=True,
            )

        self.assertTrue(enabled)
        self.assertEqual(ctx["decision"], "enabled")
        self.assertIn("--upload", ctx["reason"])

    def test_env_auto_upload_enables(self):
        with patch.dict(
            os.environ,
            {"YOUTUBE_AUTO_UPLOAD": "true"},
            clear=True,
        ):
            enabled, ctx = resolve_upload_settings(
                cli_upload=False,
            )

        self.assertTrue(enabled)
        self.assertIn("YOUTUBE_AUTO_UPLOAD", ctx["reason"])

    def test_dry_run_blocks(self):
        with patch.dict(
            os.environ,
            {
                "YOUTUBE_AUTO_UPLOAD": "true",
                "YOUTUBE_DRY_RUN": "true",
            },
            clear=True,
        ):
            enabled, ctx = resolve_upload_settings(
                cli_upload=True,
            )

        self.assertFalse(enabled)
        self.assertEqual(ctx["decision"], "blocked")
        self.assertIn("DRY_RUN", ctx["reason"])

    def test_publish_disabled_blocks(self):
        with patch.dict(
            os.environ,
            {"YOUTUBE_PUBLISH_ENABLED": "false"},
            clear=True,
        ):
            enabled, ctx = resolve_upload_settings(
                cli_upload=True,
            )

        self.assertFalse(enabled)
        self.assertIn("PUBLISH_ENABLED", ctx["reason"])

    def test_cli_overrides_when_env_disabled(self):
        with patch.dict(
            os.environ,
            {"YOUTUBE_AUTO_UPLOAD": "false"},
            clear=True,
        ):
            enabled, _ = resolve_upload_settings(
                cli_upload=True,
            )

        self.assertTrue(enabled)


if __name__ == "__main__":
    unittest.main()
