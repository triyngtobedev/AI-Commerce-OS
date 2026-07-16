"""
Testes unitários do módulo de autenticação YouTube.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.publisher.youtube_auth import (
    CredentialStatus,
    get_env_credentials,
    save_credentials_to_env,
    validate_credentials,
    _is_placeholder,
)


class TestPlaceholderDetection(unittest.TestCase):

    def test_empty_is_placeholder(self):
        self.assertTrue(_is_placeholder(""))
        self.assertTrue(_is_placeholder("   "))

    def test_real_values_not_placeholder(self):
        self.assertFalse(
            _is_placeholder(
                "123.apps.googleusercontent.com"
            )
        )
        self.assertFalse(
            _is_placeholder("1//0gRefreshTokenExample")
        )


class TestValidateCredentials(unittest.TestCase):

    def test_all_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            status = validate_credentials()

        self.assertFalse(status.configured)
        self.assertFalse(status.valid)
        self.assertEqual(len(status.missing), 3)

    def test_all_present(self):
        env = {
            "YOUTUBE_CLIENT_ID": (
                "123456.apps.googleusercontent.com"
            ),
            "YOUTUBE_CLIENT_SECRET": "secret123",
            "YOUTUBE_REFRESH_TOKEN": "1//0gToken",
        }

        with patch.dict(os.environ, env, clear=True):
            status = validate_credentials()

        self.assertTrue(status.configured)
        self.assertTrue(status.valid)
        self.assertEqual(len(status.missing), 0)

    def test_invalid_client_id_format(self):
        env = {
            "YOUTUBE_CLIENT_ID": "invalid_id",
            "YOUTUBE_CLIENT_SECRET": "secret123",
            "YOUTUBE_REFRESH_TOKEN": "1//0gToken",
        }

        with patch.dict(os.environ, env, clear=True):
            status = validate_credentials()

        self.assertTrue(status.configured)
        self.assertFalse(status.valid)
        self.assertIn("YOUTUBE_CLIENT_ID", status.invalid)

    def test_connection_test_with_mock(self):
        env = {
            "YOUTUBE_CLIENT_ID": (
                "123456.apps.googleusercontent.com"
            ),
            "YOUTUBE_CLIENT_SECRET": "secret123",
            "YOUTUBE_REFRESH_TOKEN": "1//0gToken",
        }

        with patch.dict(os.environ, env, clear=True):
            with patch(
                "scripts.publisher.youtube_auth._test_api_connection",
                return_value={
                    "ok": True,
                    "channel_id": "UC123",
                    "channel_title": "Test Channel",
                },
            ):
                status = validate_credentials(
                    test_connection=True
                )

        self.assertTrue(status.valid)
        self.assertEqual(
            status.channel_title,
            "Test Channel",
        )


class TestSaveCredentials(unittest.TestCase):

    def test_creates_new_env_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"

            save_credentials_to_env(
                "id.apps.googleusercontent.com",
                "secret",
                "refresh_token",
                env_path=env_path,
            )

            content = env_path.read_text(encoding="utf-8")

            self.assertIn(
                "YOUTUBE_CLIENT_ID=id.apps.googleusercontent.com",
                content,
            )
            self.assertIn(
                "YOUTUBE_CLIENT_SECRET=secret",
                content,
            )
            self.assertIn(
                "YOUTUBE_REFRESH_TOKEN=refresh_token",
                content,
            )

    def test_updates_existing_env_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "GEMINI_API_KEY=abc\n"
                "YOUTUBE_CLIENT_ID=old_id\n"
                "YOUTUBE_CLIENT_SECRET=old_secret\n",
                encoding="utf-8",
            )

            save_credentials_to_env(
                "new_id.apps.googleusercontent.com",
                "new_secret",
                "new_token",
                env_path=env_path,
            )

            content = env_path.read_text(encoding="utf-8")

            self.assertIn("GEMINI_API_KEY=abc", content)
            self.assertIn(
                "YOUTUBE_CLIENT_ID="
                "new_id.apps.googleusercontent.com",
                content,
            )
            self.assertNotIn("old_id", content)
            self.assertIn(
                "YOUTUBE_REFRESH_TOKEN=new_token",
                content,
            )


class TestGetEnvCredentials(unittest.TestCase):

    def test_strips_whitespace(self):
        env = {
            "YOUTUBE_CLIENT_ID": "  id.apps.googleusercontent.com  ",
            "YOUTUBE_CLIENT_SECRET": " secret ",
            "YOUTUBE_REFRESH_TOKEN": " token ",
        }

        with patch.dict(os.environ, env, clear=True):
            creds = get_env_credentials()

        self.assertEqual(
            creds["client_id"],
            "id.apps.googleusercontent.com",
        )


if __name__ == "__main__":
    unittest.main()
