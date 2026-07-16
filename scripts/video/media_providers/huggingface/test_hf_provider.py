"""
Testes do HuggingFaceProvider e adapter (sem rede real).
"""

from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from scripts.video.media_asset import MediaKind
from scripts.video.media_providers.huggingface.errors import (
    HFAuthError,
    HFConfigError,
    HFErrorCode,
    HFModelLoadingError,
    HFQualityError,
    HFSchemaError,
)
from scripts.video.media_providers.huggingface.provider import (
    FALLBACK_PROVIDER,
    HuggingFaceProvider,
    MODEL_ID,
    PRIMARY_PROVIDER,
)

PROBE = "scripts.video.media_providers.huggingface.provider"

IMAGE_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 20_000


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        content: bytes = b"",
        headers: dict[str, str] | None = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}
        self.text = text


class FakeSession:
    def __init__(self, steps: list[FakeResponse | BaseException]) -> None:
        self._steps = list(steps)
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def post(self, *args: object, **kwargs: object) -> FakeResponse:
        self.calls.append(("post", args, kwargs))
        step = self._steps.pop(0)
        if isinstance(step, BaseException):
            raise step
        return step

    def get(self, *args: object, **kwargs: object) -> FakeResponse:
        self.calls.append(("get", args, kwargs))
        step = self._steps.pop(0)
        if isinstance(step, BaseException):
            raise step
        return step


def _provider(steps: list[FakeResponse | BaseException], **kwargs: object) -> HuggingFaceProvider:
    return HuggingFaceProvider(
        api_token="hf_test_token",
        session=FakeSession(steps),
        **kwargs,
    )


def _loading() -> FakeResponse:
    return FakeResponse(status_code=503, text='{"error":"Model is currently loading"}')


def _fal_ok(url: str = "https://cdn.example.com/img.jpg") -> FakeResponse:
    body = json.dumps(
        {
            "images": [
                {"url": url, "width": 1024, "height": 576, "content_type": "image/jpeg"},
            ],
        }
    )
    return FakeResponse(status_code=200, text=body, headers={"Content-Type": "application/json"})


def _download_ok(content: bytes = IMAGE_BYTES) -> FakeResponse:
    return FakeResponse(status_code=200, content=content, headers={"Content-Type": "image/jpeg"})


def _together_ok(content: bytes = IMAGE_BYTES) -> FakeResponse:
    encoded = base64.b64encode(content).decode()
    body = json.dumps({"data": [{"b64_json": encoded}]})
    return FakeResponse(status_code=200, text=body, headers={"Content-Type": "application/json"})


class TestSuccessfulGeneration(unittest.TestCase):
    @patch(f"{PROBE}.probe_dimensions", return_value=(1024, 576))
    @patch(f"{PROBE}.time.sleep")
    def test_successful_image_fal_ai(self, _sleep: object, _probe: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "scene.jpg"
            provider = _provider([_fal_ok(), _download_ok()])
            asset = provider.generate_image("documentary scene", output_path=out)

            self.assertTrue(asset.is_image)
            self.assertEqual(asset.source, "huggingface")
            self.assertEqual(asset.width, 1024)

    @patch(f"{PROBE}.probe_dimensions", return_value=(1024, 576))
    @patch(f"{PROBE}.time.sleep")
    def test_on_metrics_success(self, _sleep: object, _probe: object) -> None:
        captured: list[dict[str, object]] = []

        def on_metrics(snapshot: dict[str, object]) -> None:
            captured.append(dict(snapshot))

        with tempfile.TemporaryDirectory() as tmp:
            provider = _provider([_fal_ok(), _download_ok()], on_metrics=on_metrics)
            provider.generate_image("scene", output_path=Path(tmp) / "s.png")

        self.assertEqual(len(captured), 1)
        self.assertTrue(captured[0]["success"])
        self.assertEqual(captured[0]["model_id"], MODEL_ID)
        self.assertEqual(captured[0]["provider"], PRIMARY_PROVIDER)


class TestRetryAndFallback(unittest.TestCase):
    @patch(f"{PROBE}.probe_dimensions", return_value=(1024, 576))
    @patch(f"{PROBE}.time.sleep")
    def test_retry_503_resolved_on_third_attempt(self, _sleep: object, _probe: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            provider = _provider([_loading(), _loading(), _fal_ok(), _download_ok()])
            asset = provider.generate_image("scene", output_path=Path(tmp) / "s.png")
            self.assertEqual(asset.source, "huggingface")
            post_calls = [c for c in provider._session.calls if c[0] == "post"]  # type: ignore[attr-defined]
            self.assertEqual(len(post_calls), 3)

    @patch(f"{PROBE}.probe_dimensions", return_value=(768, 768))
    @patch(f"{PROBE}.time.sleep")
    def test_fallback_provider_after_persistent_503(self, _sleep: object, _probe: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            steps = [_loading(), _loading(), _loading(), _together_ok()]
            provider = _provider(steps)
            asset = provider.generate_image("scene", output_path=Path(tmp) / "s.png")

            self.assertEqual(asset.source, "huggingface")
            post_urls = [str(call[1][0]) for call in provider._session.calls if call[0] == "post"]  # type: ignore[attr-defined]
            self.assertTrue(any("fal-ai" in url for url in post_urls))
            self.assertTrue(any("together" in url for url in post_urls))

    @patch(f"{PROBE}.time.sleep")
    def test_retry_exhausted_raises_model_loading_error(self, _sleep: object) -> None:
        steps = [_loading(), _loading(), _loading(), _loading()]
        provider = _provider(steps)
        with self.assertRaises(HFModelLoadingError) as ctx:
            provider.generate_image("scene")
        self.assertEqual(ctx.exception.code, HFErrorCode.MODEL_LOADING)


class TestAuthAndSchema(unittest.TestCase):
    def test_401_raises_auth_without_retry(self) -> None:
        provider = _provider([FakeResponse(status_code=401, text="Unauthorized")])
        with self.assertRaises(HFAuthError):
            provider.generate_image("scene")
        post_calls = [c for c in provider._session.calls if c[0] == "post"]  # type: ignore[attr-defined]
        self.assertEqual(len(post_calls), 1)

    def test_invalid_fal_response_raises_schema_error(self) -> None:
        provider = _provider([FakeResponse(status_code=200, text='{"bad": true}')])
        with self.assertRaises(HFSchemaError):
            provider.generate_image("scene")

    @patch(f"{PROBE}.probe_dimensions", return_value=(256, 256))
    def test_quality_below_threshold(self, _probe: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "small.png"
            provider = _provider([_fal_ok(), _download_ok()])
            with self.assertRaises(HFQualityError) as ctx:
                provider.generate_image("scene", output_path=out)
            self.assertEqual(ctx.exception.code, HFErrorCode.QUALITY_THRESHOLD)


class TestConfigAndAdapter(unittest.TestCase):
    def test_missing_token_raises_config_error(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(HFConfigError):
                HuggingFaceProvider(api_token="")

    @patch.dict("os.environ", {}, clear=True)
    def test_adapter_returns_false_without_token(self) -> None:
        from scripts.video.media_providers.huggingface import adapter

        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(adapter.generate_hf_image("x", Path(tmp) / "s.jpg"))

    @patch.dict("os.environ", {"HF_TOKEN": "hf_test_token"})
    @patch(f"{PROBE}.probe_dimensions", return_value=(1024, 576))
    def test_adapter_returns_true_on_success(self, _probe: object) -> None:
        from scripts.video.media_providers.huggingface import adapter

        with tempfile.TemporaryDirectory() as tmp:
            requested = Path(tmp) / "scene.jpg"
            png_path = requested.with_suffix(".png")
            png_path.write_bytes(IMAGE_BYTES)
            with patch.object(adapter, "HuggingFaceProvider") as fake_cls:
                fake_cls.return_value.generate_image.return_value = __import__(
                    "scripts.video.media_asset", fromlist=["MediaAsset"]
                ).MediaAsset(
                    kind=MediaKind.IMAGE,
                    path=png_path,
                    width=1024,
                    height=576,
                    mime_type="image/png",
                    source="huggingface",
                )
                ok = adapter.generate_hf_image("x", requested)
                self.assertTrue(ok)

    @patch.dict("os.environ", {"HF_TOKEN": "hf_test_token"})
    def test_adapter_returns_false_on_hf_error(self) -> None:
        from scripts.video.media_providers.huggingface import adapter

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(adapter, "HuggingFaceProvider") as fake_cls:
                fake_cls.return_value.generate_image.side_effect = HFAuthError("bad token")
                self.assertFalse(adapter.generate_hf_image("x", Path(tmp) / "s.jpg"))

    @patch(f"{PROBE}.probe_dimensions", return_value=(1024, 576))
    def test_on_metrics_failure(self, _probe: object) -> None:
        captured: list[dict[str, object]] = []

        def on_metrics(snapshot: dict[str, object]) -> None:
            captured.append(dict(snapshot))

        provider = _provider([FakeResponse(status_code=401, text="nope")], on_metrics=on_metrics)
        with self.assertRaises(HFAuthError):
            provider.generate_image("scene")

        self.assertEqual(len(captured), 1)
        self.assertFalse(captured[0]["success"])
        self.assertEqual(captured[0]["error_code"], HFErrorCode.AUTH)

    def test_generate_video_returns_false(self) -> None:
        provider = _provider([])
        self.assertFalse(provider.generate_video("prompt"))


class TestConnectivityRetry(unittest.TestCase):
    @patch(f"{PROBE}.probe_dimensions", return_value=(1024, 576))
    @patch(f"{PROBE}.time.sleep")
    def test_connection_error_retried(self, _sleep: object, _probe: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            provider = _provider([requests.ConnectionError("offline"), _fal_ok(), _download_ok()])
            asset = provider.generate_image("scene", output_path=Path(tmp) / "s.png")
            self.assertEqual(asset.source, "huggingface")
            post_calls = [c for c in provider._session.calls if c[0] == "post"]  # type: ignore[attr-defined]
            self.assertEqual(len(post_calls), 2)


if __name__ == "__main__":
    unittest.main()
