"""
HuggingFaceProvider — geração de imagem via HF Inference Providers (router).

O endpoint legado api-inference.huggingface.co foi descontinuado (nov/2025).
Este provider usa router.huggingface.co com roteamento HF + créditos gratuitos
da conta ($0,10/mês na free tier).

Modelo: black-forest-labs/FLUX.1-schnell
  Roteado via fal-ai (providerId: fal-ai/flux/schnell) — rápido, qualidade alta,
  documentado nos Inference Providers. Fallback: together (mesmo modelo HF).
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import requests
from dotenv import load_dotenv

from scripts.video.media_asset import MediaAsset, MediaKind
from scripts.video.media_probe import probe_dimensions
from scripts.video.media_providers.huggingface.errors import (
    HFAuthError,
    HFConfigError,
    HFConnectivityError,
    HFError,
    HFErrorCode,
    HFModelLoadingError,
    HFQualityError,
    HFRateLimitError,
    HFSchemaError,
    HFTimeoutError,
)
from scripts.video.media_providers.huggingface.types import (
    FalAIImageResponse,
    HFMetrics,
    OnHFMetricsCallback,
    ProviderName,
    TogetherImageResponse,
)

load_dotenv()

logger = logging.getLogger("hf_ai")

MODEL_ID = "black-forest-labs/FLUX.1-schnell"
FALLBACK_MODEL_ID = "black-forest-labs/FLUX.1-schnell"
ROUTER_BASE = "https://router.huggingface.co"

PRIMARY_PROVIDER: ProviderName = "fal-ai"
FALLBACK_PROVIDER: ProviderName = "together"
PRIMARY_ROUTE = f"{ROUTER_BASE}/fal-ai/fal-ai/flux/schnell"
FALLBACK_ROUTE = f"{ROUTER_BASE}/together/v1/images/generations"

DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 576
DEFAULT_NUM_INFERENCE_STEPS = 4

MIN_IMAGE_WIDTH = 512
MIN_IMAGE_HEIGHT = 512

MAX_ATTEMPTS = 3
RETRY_BACKOFF_BASE = 0.5
REQUEST_TIMEOUT = 90

MIME_TO_EXT: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/jpg": ".jpg",
}

ALLOWED_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/jpg"})


@dataclass(frozen=True)
class _HTTPAttemptResult:
    status_code: int
    content: bytes
    content_type: str
    text: str


@dataclass(frozen=True)
class _ProviderRoute:
    provider: ProviderName | str
    url: str
    model_id: str


class HuggingFaceProvider:
    """Cliente text-to-image via HF Inference Providers (router)."""

    def __init__(
        self,
        *,
        api_token: str | None = None,
        session: requests.Session | None = None,
        request_timeout: int = REQUEST_TIMEOUT,
        on_metrics: OnHFMetricsCallback | None = None,
    ) -> None:
        if api_token is not None:
            token = api_token
        else:
            from scripts.utils.hf_token import get_hf_token

            token = get_hf_token()
        if not token:
            raise HFConfigError(
                "HF_API_TOKEN ou HF_TOKEN ausente — configure em .env ou huggingface.co/settings/tokens"
            )

        self._token = token
        self._session = session or requests.Session()
        self._request_timeout = request_timeout
        self._on_metrics = on_metrics

    def generate_image(
        self,
        prompt: str,
        *,
        output_path: Path | None = None,
        min_width: int = MIN_IMAGE_WIDTH,
        min_height: int = MIN_IMAGE_HEIGHT,
    ) -> MediaAsset:
        started = time.perf_counter()
        attempts = 0
        error_code: HFErrorCode | None = None
        model_used = MODEL_ID
        provider_used: ProviderName | str = PRIMARY_PROVIDER

        try:
            content, mime_type, attempts, provider_used = self._generate_bytes(
                prompt,
                _ProviderRoute(PRIMARY_PROVIDER, PRIMARY_ROUTE, MODEL_ID),
            )
            model_used = MODEL_ID
            return self._materialize_asset(
                prompt,
                content,
                mime_type,
                output_path,
                model_used,
                min_width,
                min_height,
            )
        except HFModelLoadingError:
            attempts = max(attempts, MAX_ATTEMPTS)
            logger.warning(
                "Rota primária indisponível após %d tentativas — fallback %s",
                MAX_ATTEMPTS,
                FALLBACK_PROVIDER,
                extra={"model": MODEL_ID, "kind": "image", "attempt": MAX_ATTEMPTS},
            )
            try:
                content, mime_type, fallback_attempts, provider_used = self._generate_bytes(
                    prompt,
                    _ProviderRoute(FALLBACK_PROVIDER, FALLBACK_ROUTE, FALLBACK_MODEL_ID),
                    max_attempts=1,
                )
                attempts += fallback_attempts
                model_used = FALLBACK_MODEL_ID
                return self._materialize_asset(
                    prompt,
                    content,
                    mime_type,
                    output_path,
                    model_used,
                    min_width,
                    min_height,
                )
            except HFError as fallback_error:
                error_code = fallback_error.code
                raise HFModelLoadingError(
                    f"Rotas {PRIMARY_PROVIDER} e {FALLBACK_PROVIDER} indisponíveis para {MODEL_ID}",
                    details={
                        "primary_provider": PRIMARY_PROVIDER,
                        "fallback_provider": FALLBACK_PROVIDER,
                        "model_id": MODEL_ID,
                    },
                ) from fallback_error
        except HFError as error:
            error_code = error.code
            raise
        finally:
            if self._on_metrics is not None:
                duration_ms = int((time.perf_counter() - started) * 1000)
                self._emit_metrics(
                    success=error_code is None,
                    error_code=error_code,
                    duration_ms=duration_ms,
                    attempts=attempts,
                    model_id=model_used,
                    provider=provider_used,
                )

    def generate_video(
        self,
        prompt: str,
        *,
        output_path: Path | None = None,
    ) -> bool:
        _ = (prompt, output_path)
        return False

    def _emit_metrics(
        self,
        *,
        success: bool,
        error_code: HFErrorCode | None,
        duration_ms: int,
        attempts: int,
        model_id: str,
        provider: ProviderName | str,
    ) -> None:
        if self._on_metrics is None:
            return
        snapshot: HFMetrics = {
            "kind": "image",
            "success": success,
            "error_code": error_code,
            "duration_ms": duration_ms,
            "attempts": attempts,
            "model_id": model_id,
            "provider": provider,
        }
        try:
            self._on_metrics(snapshot)
        except Exception:  # pragma: no cover
            logger.exception(
                "Callback on_metrics falhou",
                extra={"model": model_id, "kind": "image", "attempt": 0},
            )

    def _generate_bytes(
        self,
        prompt: str,
        route: _ProviderRoute,
        *,
        max_attempts: int = MAX_ATTEMPTS,
    ) -> tuple[bytes, str, int, ProviderName | str]:
        headers = {"Authorization": f"Bearer {self._token}"}
        last_loading_error: HFModelLoadingError | None = None

        for attempt in range(1, max_attempts + 1):
            logger.info(
                "Gerando imagem HF",
                extra={"model": route.model_id, "kind": "image", "attempt": attempt},
            )
            payload = self._build_payload(prompt, route)
            try:
                result = self._post(route.url, headers=headers, payload=payload)
            except (HFTimeoutError, HFConnectivityError) as error:
                if attempt >= max_attempts:
                    raise
                self._sleep_backoff(attempt)
                last_loading_error = None
                continue

            if result.status_code == 200:
                content, mime = self._extract_image_bytes(result, route)
                return content, mime, attempt, route.provider

            retryable = self._handle_http_error(result, route.model_id, attempt)
            if retryable and attempt < max_attempts:
                if isinstance(retryable, HFModelLoadingError):
                    last_loading_error = retryable
                self._sleep_backoff(attempt)
                continue
            if isinstance(retryable, HFError):
                raise retryable

        if last_loading_error is not None:
            raise last_loading_error
        raise HFModelLoadingError(
            f"Rota {route.provider} indisponível após {max_attempts} tentativas",
            details={"model_id": route.model_id, "provider": route.provider, "attempts": max_attempts},
        )

    @staticmethod
    def _build_payload(prompt: str, route: _ProviderRoute) -> Mapping[str, object]:
        if route.provider == PRIMARY_PROVIDER:
            return {
                "prompt": prompt,
                "image_size": {"width": DEFAULT_WIDTH, "height": DEFAULT_HEIGHT},
                "num_inference_steps": DEFAULT_NUM_INFERENCE_STEPS,
            }
        return {
            "prompt": prompt,
            "model": route.model_id,
            "width": DEFAULT_WIDTH,
            "height": DEFAULT_HEIGHT,
            "steps": DEFAULT_NUM_INFERENCE_STEPS,
            "response_format": "base64",
        }

    def _extract_image_bytes(self, result: _HTTPAttemptResult, route: _ProviderRoute) -> tuple[bytes, str]:
        if route.provider == PRIMARY_PROVIDER:
            return self._parse_fal_ai_response(result)
        return self._parse_together_response(result)

    def _parse_fal_ai_response(self, result: _HTTPAttemptResult) -> tuple[bytes, str]:
        try:
            data = json.loads(result.text)
            parsed = _as_fal_ai_response(data)
            image_url = parsed["images"][0]["url"]
            item_type = parsed["images"][0].get("content_type", "image/jpeg")
        except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as error:
            raise HFSchemaError("Resposta fal-ai inválida", details={"body": result.text[:500]}) from error

        try:
            download = self._session.get(image_url, timeout=self._request_timeout)
        except requests.Timeout as error:
            raise HFTimeoutError("Timeout ao baixar imagem fal-ai", details={"url": image_url}) from error
        except requests.RequestException as error:
            raise HFConnectivityError("Falha ao baixar imagem fal-ai", details={"url": image_url}) from error

        if download.status_code != 200:
            raise HFConnectivityError(
                f"Download fal-ai falhou ({download.status_code})",
                details={"url": image_url},
            )

        mime = self._normalize_content_type(download.headers.get("Content-Type", item_type))
        if mime not in ALLOWED_MIME_TYPES:
            raise HFSchemaError(
                f"Content-Type inesperado no download: {mime}",
                details={"content_type": mime},
            )
        return download.content, mime

    @staticmethod
    def _parse_together_response(result: _HTTPAttemptResult) -> tuple[bytes, str]:
        try:
            data = json.loads(result.text)
            parsed = _as_together_response(data)
            encoded = parsed["data"][0]["b64_json"]
            content = base64.b64decode(encoded)
        except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as error:
            raise HFSchemaError("Resposta together inválida", details={"body": result.text[:500]}) from error

        if len(content) < 1000:
            raise HFSchemaError("Imagem together decodificada muito pequena")
        return content, "image/png"

    def _post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        payload: Mapping[str, object],
    ) -> _HTTPAttemptResult:
        try:
            response = self._session.post(
                url,
                headers=headers,
                json=payload,
                timeout=self._request_timeout,
            )
        except requests.Timeout as error:
            raise HFTimeoutError("Timeout na requisição HF", details={"url": url}) from error
        except requests.RequestException as error:
            raise HFConnectivityError("Falha de conectividade HF", details={"url": url}) from error

        content_type = response.headers.get("Content-Type", "")
        return _HTTPAttemptResult(
            status_code=response.status_code,
            content=response.content,
            content_type=content_type,
            text=response.text,
        )

    def _handle_http_error(
        self,
        result: _HTTPAttemptResult,
        model_id: str,
        attempt: int,
    ) -> HFError | None:
        status = result.status_code
        details: dict[str, object] = {
            "status_code": status,
            "model_id": model_id,
            "attempt": attempt,
            "body": result.text[:500],
        }

        if status in {401, 403}:
            raise HFAuthError(f"Autenticação HF rejeitada ({status})", details=details)
        if status in {400, 404}:
            raise HFSchemaError(f"Requisição HF inválida ({status})", details=details)
        if status == 429:
            raise HFRateLimitError("Rate limit HF excedido", details=details)
        if status == 503:
            return HFModelLoadingError("Modelo HF carregando (503)", details=details)
        if status == 504:
            return HFTimeoutError("Gateway timeout HF (504)", details=details)
        if status >= 500:
            return HFConnectivityError(f"Erro de servidor HF ({status})", details=details)

        if self._looks_like_json_error(result):
            raise HFSchemaError("Resposta HF em JSON de erro", details=details)
        raise HFSchemaError(f"Resposta HF inesperada ({status})", details=details)

    @staticmethod
    def _looks_like_json_error(result: _HTTPAttemptResult) -> bool:
        content_type = result.content_type.lower()
        if "application/json" in content_type:
            return True
        stripped = result.text.lstrip()
        return stripped.startswith("{")

    @staticmethod
    def _normalize_content_type(raw: str) -> str:
        return raw.split(";", 1)[0].strip().lower()

    @staticmethod
    def _sleep_backoff(attempt: int) -> None:
        delay = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
        time.sleep(delay)

    def _materialize_asset(
        self,
        prompt: str,
        content: bytes,
        mime_type: str,
        output_path: Path | None,
        model_id: str,
        min_width: int,
        min_height: int,
    ) -> MediaAsset:
        ext = MIME_TO_EXT.get(mime_type, ".png")
        target = Path(output_path) if output_path is not None else Path(f"hf_image{ext}")
        if target.suffix.lower() != ext:
            target = target.with_suffix(ext)

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

        width, height = probe_dimensions(target)
        if width < min_width or height < min_height:
            if target.exists():
                target.unlink()
            raise HFQualityError(
                f"Imagem abaixo do mínimo ({width}x{height} < {min_width}x{min_height})",
                details={"width": width, "height": height, "model_id": model_id},
            )

        return MediaAsset(
            kind=MediaKind.IMAGE,
            path=target,
            width=width,
            height=height,
            mime_type=mime_type,
            source="huggingface",
            prompt=prompt,
            file_size_bytes=target.stat().st_size,
        )


def _as_fal_ai_response(data: object) -> FalAIImageResponse:
    if not isinstance(data, dict):
        raise ValueError("expected dict")
    images = data.get("images")
    if not isinstance(images, list) or not images:
        raise ValueError("missing images")
    first = images[0]
    if not isinstance(first, dict) or not isinstance(first.get("url"), str):
        raise ValueError("invalid image item")
    return {"images": [{"url": first["url"], **{k: v for k, v in first.items() if k != "url"}}]}  # type: ignore[typeddict-item]


def _as_together_response(data: object) -> TogetherImageResponse:
    if not isinstance(data, dict):
        raise ValueError("expected dict")
    rows = data.get("data")
    if not isinstance(rows, list) or not rows:
        raise ValueError("missing data")
    first = rows[0]
    if not isinstance(first, dict) or not isinstance(first.get("b64_json"), str):
        raise ValueError("invalid data item")
    return {"data": [{"b64_json": first["b64_json"]}]}
