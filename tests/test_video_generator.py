"""
Testes unitários do VideoGenerator com mocks (sem chamadas reais às APIs).

Uso:
    pytest tests/test_video_generator.py -v
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.prompt_builder import build_prompt  # noqa: E402
from src.video_generator import (  # noqa: E402
    CaptchaError,
    NoCreditError,
    VideoGenerationResult,
    VideoGenerator,
)

DEFAULT_PROMPT = "wireless earbuds on white surface, product showcase"
DEFAULT_PRODUCT = "Earbuds Pro"
OUTPUT_DIR = _PROJECT_ROOT / "output" / "videos"


def _make_result(
    *,
    api_used: str = "falai",
    video_url: str = "https://example.com/video.mp4",
    resolution: str = "480p",
) -> VideoGenerationResult:
    return VideoGenerationResult(
        video_url=video_url,
        api_used=api_used,
        credits_remaining=None,
        duration_seconds=1.0,
        resolution=resolution,
    )


# ---------------------------------------------------------------------------
# prompt_builder
# ---------------------------------------------------------------------------


class TestPromptBuilder:
    """Valida adaptação de prompts por API."""

    def test_i2v_prompt_movements(self) -> None:
        for movement in ("zoom", "rotate", "float", "reveal"):
            from src.prompt_builder import build_ecommerce_i2v_prompt

            bundle = build_ecommerce_i2v_prompt("Sneaker Pro", movement=movement)  # type: ignore[arg-type]
            assert "[MOVEMENT]" in bundle["prompt"]
            assert "[PRODUCT FOCUS]" in bundle["prompt"]
            assert "Sneaker Pro" in bundle["prompt"]
            assert bundle["negative_prompt"] is not None

    def test_no_4k_in_any_api(self) -> None:
        for api in ("falai", "replicate", "kling_web"):
            bundle = build_prompt(DEFAULT_PRODUCT, api)  # type: ignore[arg-type]
            assert "4K" not in bundle["prompt"]
            assert "4k" not in bundle["prompt"].lower()
            assert "sharp" in bundle["prompt"].lower()

    def test_falai_inlines_negative(self) -> None:
        bundle = build_prompt(DEFAULT_PRODUCT, "falai")
        assert bundle["negative_prompt"] is None
        assert "[Avoid]" in bundle["prompt"]
        assert "watermark" in bundle["prompt"]

    def test_kling_web_separate_negative(self) -> None:
        bundle = build_prompt(DEFAULT_PRODUCT, "kling_web")
        assert bundle["negative_prompt"] is not None
        assert "watermark" in bundle["negative_prompt"]
        assert "[Avoid]" not in bundle["prompt"]

    def test_get_best_movement_by_category(self) -> None:
        from src.prompt_builder import get_best_movement

        assert get_best_movement("Casa") == "float"
        assert get_best_movement("Tecnologia") == "zoom"
        assert get_best_movement("Automotivo") == "reveal"
        assert get_best_movement("Moda") == "rotate"

    def test_get_best_movement_defaults_to_zoom(self) -> None:
        from src.prompt_builder import get_best_movement

        assert get_best_movement("") == "zoom"
        assert get_best_movement("categoria-inexistente") == "zoom"

    def test_build_scene_video_prompt_youtube_dark(self) -> None:
        from src.prompt_builder import build_scene_video_prompt

        bundle = build_scene_video_prompt(
            scene_description="Ancient Roman aqueduct at sunset",
            scene_query="roman aqueduct ruins documentary",
            platform="youtube",
            scene_tipo="contexto",
            emotion="tension",
        )
        assert "[SCENE]" in bundle["prompt"]
        assert "16:9" in bundle["prompt"] or "landscape" in bundle["prompt"]
        assert "documentary" in bundle["prompt"].lower()
        assert bundle["negative_prompt"] is not None
        assert "cartoon" in bundle["negative_prompt"]


# ---------------------------------------------------------------------------
# fal.ai mock
# ---------------------------------------------------------------------------


class TestFalaiGeneration:
    """Testa _generate_falai com HTTP mockado."""

    def test_falai_success(self) -> None:
        generator = VideoGenerator(output_dir=OUTPUT_DIR)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"video_url": "https://cdn.example.com/fal.mp4"}
        mock_response.content = b"{}"
        mock_response.text = "{}"

        with (
            patch.dict(os.environ, {"HF_API_TOKEN": "hf_test_token"}),
            patch.object(generator._session, "request", return_value=mock_response),
        ):
            result = generator._generate_falai("product video prompt", None)

        assert result.api_used == "falai"
        assert result.resolution == "480p"
        assert result.video_url == "https://cdn.example.com/fal.mp4"

    def test_falai_missing_token(self) -> None:
        generator = VideoGenerator()
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="HF_API_TOKEN"):
                generator._generate_falai("prompt", None)

    def test_falai_poll_202_then_success(self) -> None:
        generator = VideoGenerator(output_dir=OUTPUT_DIR)
        pending = MagicMock()
        pending.status_code = 202
        pending.headers = {}
        pending.json.return_value = {"status": "processing", "status_url": "https://poll.example/status"}
        pending.content = b""
        pending.text = ""

        done = MagicMock()
        done.status_code = 200
        done.headers = {"Content-Type": "application/json"}
        done.json.return_value = {"status": "succeeded", "video_url": "https://cdn.example.com/done.mp4"}
        done.content = b""
        done.text = ""

        with (
            patch.dict(os.environ, {"HF_API_TOKEN": "hf_test"}),
            patch.object(generator._session, "request", return_value=pending),
            patch.object(generator._session, "get", return_value=done),
            patch("src.video_generator.time.sleep"),
        ):
            result = generator._generate_falai("prompt", "https://img.example/a.jpg")

        assert result.video_url == "https://cdn.example.com/done.mp4"


# ---------------------------------------------------------------------------
# Replicate mock
# ---------------------------------------------------------------------------


class TestReplicateGeneration:
    """Testa _generate_replicate com HTTP mockado."""

    def test_replicate_success(self) -> None:
        generator = VideoGenerator(output_dir=OUTPUT_DIR)

        create_resp = MagicMock()
        create_resp.status_code = 201
        create_resp.json.return_value = {"id": "pred-123", "status": "starting"}

        poll_resp = MagicMock()
        poll_resp.status_code = 200
        poll_resp.json.return_value = {
            "id": "pred-123",
            "status": "succeeded",
            "output": "https://replicate.delivery/output.mp4",
        }

        with (
            patch.dict(os.environ, {"REPLICATE_API_TOKEN": "r8_test"}),
            patch.object(generator._session, "post", return_value=create_resp),
            patch.object(generator._session, "get", return_value=poll_resp),
            patch("src.video_generator.time.sleep"),
        ):
            result = generator._generate_replicate("prompt text", None)

        assert result.api_used == "replicate"
        assert result.video_url == "https://replicate.delivery/output.mp4"

    def test_replicate_timeout(self) -> None:
        generator = VideoGenerator(output_dir=OUTPUT_DIR)

        create_resp = MagicMock()
        create_resp.status_code = 201
        create_resp.json.return_value = {"id": "pred-slow", "status": "processing"}

        poll_resp = MagicMock()
        poll_resp.status_code = 200
        poll_resp.json.return_value = {"id": "pred-slow", "status": "processing"}

        tick = 0

        def fake_time() -> float:
            nonlocal tick
            tick += 50
            return float(tick)

        with (
            patch.dict(os.environ, {"REPLICATE_API_TOKEN": "r8_test", "VIDEO_TIMEOUT": "30"}),
            patch.object(generator._session, "post", return_value=create_resp),
            patch.object(generator._session, "get", return_value=poll_resp),
            patch("src.video_generator.time.sleep"),
            patch("src.video_generator.time.time", side_effect=fake_time),
        ):
            with pytest.raises(TimeoutError, match="Replicate polling timeout"):
                generator._generate_replicate("prompt", None)


# ---------------------------------------------------------------------------
# Fallback chain
# ---------------------------------------------------------------------------


class TestVideoGeneratorFallback:
    """Testa cadeia fal.ai → Replicate → Kling Web."""

    def test_primary_falai_success(self) -> None:
        generator = VideoGenerator(output_dir=OUTPUT_DIR)
        with (
            patch.object(
                generator,
                "_generate_falai",
                return_value=_make_result(api_used="falai"),
            ),
            patch.object(generator, "_download_video", return_value=None),
        ):
            result = generator.generate(
                DEFAULT_PROMPT,
                product_name=DEFAULT_PRODUCT,
                download=False,
            )

        assert result["api_used"] == "falai"
        assert result["resolution"] == "480p"
        assert result["fallback_reason"] is None

    def test_fallback_falai_to_replicate(self) -> None:
        generator = VideoGenerator(output_dir=OUTPUT_DIR)
        with (
            patch.object(
                generator,
                "_generate_falai",
                side_effect=RuntimeError("HF créditos esgotados"),
            ),
            patch.object(
                generator,
                "_generate_replicate",
                return_value=_make_result(api_used="replicate"),
            ),
            patch.object(generator, "_download_video", return_value=None),
        ):
            result = generator.generate(DEFAULT_PROMPT, download=False)

        assert result["api_used"] == "replicate"
        assert result["fallback_reason"] is not None
        assert "falai" in result["fallback_reason"]

    def test_full_fallback_to_kling_web(self) -> None:
        generator = VideoGenerator(output_dir=OUTPUT_DIR)
        with (
            patch.object(generator, "_generate_falai", side_effect=RuntimeError("fal down")),
            patch.object(generator, "_generate_replicate", side_effect=RuntimeError("rep down")),
            patch.object(
                generator,
                "_generate_kling_web_sync",
                return_value=_make_result(api_used="kling_web", resolution="720p"),
            ),
            patch.object(generator, "_download_video", return_value=None),
        ):
            result = generator.generate(DEFAULT_PROMPT, download=False)

        assert result["api_used"] == "kling_web"
        assert result["resolution"] == "720p"
        assert "replicate" in (result["fallback_reason"] or "")

    def test_all_apis_fail(self) -> None:
        generator = VideoGenerator()
        with (
            patch.object(generator, "_generate_falai", side_effect=RuntimeError("fal")),
            patch.object(generator, "_generate_replicate", side_effect=RuntimeError("rep")),
            patch.object(generator, "_generate_kling_web_sync", side_effect=RuntimeError("kling")),
        ):
            with pytest.raises(RuntimeError, match="Todas as APIs"):
                generator.generate(DEFAULT_PROMPT, download=False)


# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------


class TestRetryAndTimeout:
    """Testa retry com backoff e rate limit."""

    def test_retry_then_success(self) -> None:
        generator = VideoGenerator(output_dir=OUTPUT_DIR)
        call_count = 0

        def flaky(*_args: object, **_kwargs: object) -> VideoGenerationResult:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("429 rate limit")
            return _make_result()

        with (
            patch.object(generator, "_generate_falai", side_effect=flaky),
            patch.object(generator, "_download_video", return_value=None),
            patch("src.video_generator.time.sleep"),
        ):
            result = generator.generate(DEFAULT_PROMPT, download=False)

        assert result["api_used"] == "falai"
        assert call_count == 2

    def test_kling_captcha_propagates(self) -> None:
        generator = VideoGenerator()
        with (
            patch.object(generator, "_generate_falai", side_effect=RuntimeError("skip")),
            patch.object(generator, "_generate_replicate", side_effect=RuntimeError("skip")),
            patch.object(
                generator,
                "_generate_kling_web_sync",
                side_effect=CaptchaError("CAPTCHA"),
            ),
        ):
            with pytest.raises(RuntimeError, match="Todas as APIs"):
                generator.generate(DEFAULT_PROMPT, download=False)

        summary = generator.get_attempt_summary()
        assert any("kling_web" in log["api"] for log in summary)

    def test_kling_no_credit_propagates(self) -> None:
        generator = VideoGenerator()
        with (
            patch.object(generator, "_generate_falai", side_effect=RuntimeError("skip")),
            patch.object(generator, "_generate_replicate", side_effect=RuntimeError("skip")),
            patch.object(
                generator,
                "_generate_kling_web_sync",
                side_effect=NoCreditError("sem créditos"),
            ),
        ):
            with pytest.raises(RuntimeError, match="Todas as APIs"):
                generator.generate(DEFAULT_PROMPT, download=False)


# ---------------------------------------------------------------------------
# Kling web sync wrapper
# ---------------------------------------------------------------------------


class TestKlingWebSync:
    """Testa _generate_kling_web_sync com asyncio mockado."""

    def test_kling_web_sync_delegates_to_async(self, tmp_path: Path) -> None:
        generator = VideoGenerator(output_dir=tmp_path)
        expected = _make_result(api_used="kling_web", resolution="720p")
        bundle = build_prompt(DEFAULT_PRODUCT, "kling_web")

        with patch.object(
            generator,
            "_generate_kling_web",
            new=AsyncMock(return_value=expected),
        ):
            result = generator._generate_kling_web_sync(bundle)

        assert result.api_used == "kling_web"
        assert result.resolution == "720p"


# ---------------------------------------------------------------------------
# generate_youtube_scene
# ---------------------------------------------------------------------------


def test_generate_youtube_scene_uses_t2v_params(mocker):
    """generate_youtube_scene deve usar T2V_YOUTUBE_PARAMS (steps=45, cfg=8.5)."""
    mock_replicate = mocker.patch.object(VideoGenerator, "_generate_replicate")
    mock_replicate.return_value = VideoGenerationResult(
        video_url="https://example.com/scene.mp4",
        api_used="replicate",
        credits_remaining=None,
        duration_seconds=35.0,
        resolution="1024x576",
    )
    mocker.patch.object(VideoGenerator, "_download_video", return_value=None)
    gen = VideoGenerator()
    result = gen.generate_youtube_scene(
        scene_description="Em 1941, a Alemanha lançou a Operação Barbarossa.",
        scene_query="operação barbarossa 1941 invasão",
        scene_tipo="desenvolvimento_1",
        emotion="tension",
        download=False,
    )
    call_kwargs = mock_replicate.call_args
    params_used = call_kwargs.kwargs.get("params") or {}
    assert params_used.get("steps", 0) >= 40, "steps deve ser >= 40 para YouTube T2V"
    assert params_used.get("cfg", 0) >= 8.0, "cfg deve ser >= 8.0 para YouTube T2V"
    assert result["api_used"] == "replicate"
    assert result["emotion"] == "tension"


def test_generate_youtube_scene_uses_scene_prompt(mocker):
    """generate_youtube_scene deve usar build_scene_video_prompt, não build_from_description."""
    mock_scene_prompt = mocker.patch(
        "src.video_generator.build_scene_video_prompt",
        return_value={"prompt": "test scene prompt", "negative_prompt": None},
    )
    mocker.patch.object(VideoGenerator, "_generate_replicate")
    mocker.patch.object(VideoGenerator, "_retry_with_backoff", side_effect=RuntimeError("skip"))
    gen = VideoGenerator()
    try:
        gen.generate_youtube_scene(
            scene_description="Cena teste",
            scene_query="test query",
            download=False,
        )
    except RuntimeError:
        pass
    mock_scene_prompt.assert_called_once()
    call_kwargs = mock_scene_prompt.call_args.kwargs
    assert call_kwargs.get("platform") in ("youtube_dark", "youtube")


def test_generate_youtube_scene_extracts_visual_direction(mocker):
    """generate_youtube_scene deve extrair emotion e scene_tipo do visual_direction."""
    mocker.patch.object(VideoGenerator, "_retry_with_backoff", side_effect=RuntimeError("skip"))
    gen = VideoGenerator()
    visual_dir = {
        "visual_type": "dramatic_event",
        "emotion": "sorrow",
        "section_key": "revelacao",
        "animation_strategy": "archive_footage",
    }
    captured = {}

    def capture_call(**kwargs):
        captured.update(kwargs)
        return {"prompt": "x", "negative_prompt": None}

    mocker.patch("src.video_generator.build_scene_video_prompt", side_effect=capture_call)
    try:
        gen.generate_youtube_scene(
            scene_description="Cena teste",
            scene_query="test",
            visual_direction=visual_dir,
            download=False,
        )
    except RuntimeError:
        pass
    assert captured.get("emotion") == "sorrow"
    assert captured.get("scene_tipo") == "revelacao"
