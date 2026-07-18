"""
VideoGenerator — geração de vídeo com fallback automático (custo zero real).

Ordem de fallback: fal.ai (HF Router) → Replicate → Kling Web (Playwright).

Variáveis de ambiente:
    HF_API_TOKEN          — Token Hugging Face (router fal-ai)
    REPLICATE_API_TOKEN   — Token Replicate (trial)
    KLING_EMAIL           — E-mail Kling web (fallback Playwright)
    KLING_PASSWORD        — Senha Kling web
    VIDEO_OUTPUT_DIR      — Diretório de saída (default: ./output/videos)
    VIDEO_MAX_RETRIES     — Tentativas por API (default: 3)
    VIDEO_POLL_INTERVAL   — Intervalo de poll em segundos (default: 10)
    VIDEO_TIMEOUT         — Timeout de geração/poll em segundos (default: 300)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

from src.prompt_builder import PromptBundle, build_ecommerce_i2v_prompt, build_from_description, build_scene_video_prompt

load_dotenv()

logger = logging.getLogger("video_generator")

# --- Endpoints ---

FALAI_HF_ROUTE_T2V = (
    "https://router.huggingface.co/fal-ai/fal-ai/wan/v2.2-5b/text-to-video"
)
FALAI_HF_ROUTE_I2V = (
    "https://router.huggingface.co/fal-ai/fal-ai/wan/v2.2-5b/image-to-video"
)
REPLICATE_PREDICTIONS_URL = "https://api.replicate.com/v1/predictions"
REPLICATE_MODEL = "lightricks/ltx-video"
REPLICATE_VERSION = os.getenv(
    "REPLICATE_LTX_VERSION",
    "8c47da666861d081eeb4d1261853087de23923a268a69b63febdf5dc1dee08e4",
)
KLING_APP_BASE = os.getenv("KLING_APP_BASE", "https://kling.ai")
KLING_VIDEO_NEW_PATH = "/app/video/new"
KLING_SELECTOR_TIMEOUT = int(os.getenv("KLING_SELECTOR_TIMEOUT", "20000"))
KLING_LOGIN_TIMEOUT = int(os.getenv("KLING_LOGIN_TIMEOUT", "30000"))

KLING_EMAIL_SELECTORS = (
    'input[type="email"]',
    'input[placeholder*="Email" i]',
    'input[placeholder*="email" i]',
    'input[name="email"]',
    'input[autocomplete="email"]',
)
KLING_PASSWORD_SELECTORS = (
    'input[type="password"]',
    'input[placeholder*="Password" i]',
    'input[autocomplete="current-password"]',
)
KLING_COOKIE_SELECTORS = (
    'button[id*="accept"]',
    'button[class*="accept"]',
    'button:has-text("Accept")',
    'button:has-text("Aceitar")',
    'button:has-text("Accept All")',
    'button:has-text("Got it")',
    'button:has-text("Agree")',
)
KLING_PROMO_CLOSE_SELECTORS = (
    ".el-overlay-dialog .control-btn",
    ".el-overlay .control-btn",
    ".el-dialog__headerbtn",
    'button[aria-label="Close"]',
)

# --- Config via ambiente ---

VIDEO_OUTPUT_DIR = Path(os.getenv("VIDEO_OUTPUT_DIR", "./output/videos"))
VIDEO_MAX_RETRIES = int(os.getenv("VIDEO_MAX_RETRIES", "3"))
VIDEO_POLL_INTERVAL = float(os.getenv("VIDEO_POLL_INTERVAL", "10"))
VIDEO_TIMEOUT = float(os.getenv("VIDEO_TIMEOUT", "300"))
KLING_WEB_TIMEOUT = 600.0
RETRY_BACKOFF_BASE = 1.0

# Parâmetros LTX otimizados para I2V e-commerce (lightricks/ltx-video no Replicate)
I2V_OPTIMAL_PARAMS: dict[str, Any] = {
    "length": 97,
    "target_size": 832,  # API aceita: 512,576,640,704,768,832,896,960,1024
    "cfg": 7.5,
    "steps": 30,
    "image_noise_scale": 0.12,
}

# Parâmetros LTX otimizados para T2V YouTube Dark (cenas documentais cinematográficas)
T2V_YOUTUBE_PARAMS: dict[str, Any] = {
    "length": 97,          # ~4s a 24fps — duração adequada para b-roll documental
    "target_size": 832,    # Resolução maior que o default T2V (640) — melhor qualidade
    "cfg": 8.5,            # Maior fidelidade ao prompt (vs 7.5 do I2V e-commerce)
    "steps": 45,           # Mais steps = melhor coerência visual em cenas complexas
    "aspect_ratio": "16:9",
}

I2V_RESOLUTION = "800x512"
I2V_UPSCALED_RESOLUTION = "1600x1024"

# Padrões sensíveis — nunca logar valores reais
_SENSITIVE_ENV_KEYS = frozenset(
    {
        "HF_API_TOKEN",
        "HF_TOKEN",
        "REPLICATE_API_TOKEN",
        "KLING_PASSWORD",
        "LUMA_PASSWORD",
        "KLING_EMAIL",
        "LUMA_EMAIL",
    }
)


class CaptchaError(RuntimeError):
    """CAPTCHA detectado na automação web Kling."""


class NoCreditError(RuntimeError):
    """Créditos diários Kling web esgotados."""


class ElementNotFoundError(RuntimeError):
    """Nenhum seletor Playwright encontrou o elemento alvo."""


@dataclass(frozen=True)
class VideoGenerationResult:
    """Resultado padronizado de geração de vídeo."""

    video_url: str
    api_used: str
    credits_remaining: int | None
    duration_seconds: float
    resolution: str
    fallback_reason: str | None = None
    local_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serializa o resultado para dict JSON-compatível."""
        return {
            "video_url": self.video_url,
            "api_used": self.api_used,
            "credits_remaining": self.credits_remaining,
            "duration_seconds": self.duration_seconds,
            "resolution": self.resolution,
            "fallback_reason": self.fallback_reason,
            "local_path": self.local_path,
        }


@dataclass
class _AttemptLog:
    """Log interno de tentativas por API."""

    api: str
    attempts: int = 0
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0


def _redact_message(message: str) -> str:
    """Remove possíveis tokens/credenciais de mensagens de log."""
    redacted = message
    for key in _SENSITIVE_ENV_KEYS:
        value = os.getenv(key, "")
        if value and len(value) > 4:
            redacted = redacted.replace(value, f"<{key}>")
    redacted = re.sub(r"(Bearer|Token)\s+\S+", r"\1 <redacted>", redacted, flags=re.I)
    redacted = re.sub(r"hf_[A-Za-z0-9]+", "hf_<redacted>", redacted)
    redacted = re.sub(r"r8_[A-Za-z0-9]+", "r8_<redacted>", redacted)
    return redacted


class VideoGenerator:
    """
    Gera vídeos via APIs gratuitas com fallback automático.

    Ordem: fal.ai (HF Router) → Replicate → Kling Web (Playwright)
    """

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        output_dir: Path | None = None,
    ) -> None:
        self._session = session or requests.Session()
        self._output_dir = output_dir or VIDEO_OUTPUT_DIR
        self._attempt_logs: list[_AttemptLog] = []

    def generate_i2v_ecommerce(
        self,
        product_name: str,
        image_url: str,
        *,
        material: str | None = None,
        color: str | None = None,
        movement: str = "zoom",
        download: bool = True,
        upscale: bool = True,
        replicate_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Fluxo de produção I2V e-commerce: prompt otimizado → Replicate → upscale 2x.

        Args:
            product_name: Nome do produto.
            image_url: URL da foto do produto (recomendado 800×512).
            material: Material opcional (leather, mesh, cotton).
            color: Cor opcional (white, black, red).
            movement: zoom | rotate | float | reveal.
            download: Baixa MP4 para output_dir.
            upscale: Aplica upscale 2x via ffmpeg após geração.
            replicate_params: Override dos parâmetros LTX (cfg, steps, etc.).

        Returns:
            Dict com video_url, local_path, api_used, duration_seconds, resolution, upscaled.
        """
        from src.video_upscaler import upscale_video_ffmpeg

        bundle = build_ecommerce_i2v_prompt(
            product_name,
            material=material,
            color=color,
            movement=movement,  # type: ignore[arg-type]
        )
        started = time.perf_counter()
        attempt_log = _AttemptLog(api="replicate")
        self._attempt_logs = [attempt_log]

        result = self._retry_with_backoff(
            lambda: self._generate_replicate(
                bundle["prompt"],
                image_url,
                params=replicate_params,
                negative_prompt=bundle.get("negative_prompt"),
            ),
            attempt_log,
        )

        local_path = result.local_path
        if download and result.video_url:
            downloaded = self._download_video(result.video_url, "replicate")
            if downloaded:
                local_path = str(downloaded)

        upscaled = False
        if upscale and local_path and Path(local_path).exists():
            try:
                upscaled_path = upscale_video_ffmpeg(local_path, scale=2)
                local_path = upscaled_path
                upscaled = True
            except Exception as error:
                logger.warning("Upscale I2V ignorado: %s", _redact_message(str(error)))

        resolution = I2V_UPSCALED_RESOLUTION if upscaled else I2V_RESOLUTION
        return {
            "video_url": result.video_url,
            "api_used": "replicate",
            "credits_remaining": None,
            "duration_seconds": time.perf_counter() - started,
            "resolution": resolution,
            "fallback_reason": None,
            "local_path": local_path,
            "upscaled": upscaled,
            "movement": movement,
            "prompt": bundle["prompt"],
        }

    def generate_youtube_scene(
        self,
        scene_description: str,
        scene_query: str,
        *,
        scene_tipo: str = "",
        emotion: str = "",
        visual_direction: dict | None = None,
        t2v_params: dict[str, Any] | None = None,
        download: bool = True,
    ) -> dict[str, Any]:
        """
        Gera vídeo T2V para cenas documentais YouTube Dark via Replicate LTX-Video.

        Usa build_scene_video_prompt para prompts cinematográficos e
        T2V_YOUTUBE_PARAMS para qualidade máxima no LTX.

        Args:
            scene_description: Texto narrativo da cena (narração ou descrição).
            scene_query: Query curta de busca (ex: "operação barbarossa 1941 mapa").
            scene_tipo: Tipo da cena (hook, contexto, revelacao, etc.).
            emotion: Emoção da cena (tension, sorrow, neutral).
            visual_direction: Dict retornado por VisualDirection.to_dict() — se
                fornecido, extrai scene_tipo e emotion automaticamente.
            t2v_params: Override dos parâmetros T2V_YOUTUBE_PARAMS.
            download: Se True, baixa MP4 para output_dir.

        Returns:
            Dict com video_url, local_path, api_used, duration_seconds,
            resolution, prompt usado e metadados da cena.
        """
        # Extrair metadados do visual_direction se fornecido
        if visual_direction:
            scene_tipo = scene_tipo or visual_direction.get("section_key", "")
            emotion = emotion or visual_direction.get("emotion", "")

        bundle = build_scene_video_prompt(
            scene_description=scene_description,
            scene_query=scene_query,
            platform="youtube_dark",
            style="cinematic",
            scene_tipo=scene_tipo,
            emotion=emotion,
            visual_direction=visual_direction,
        )

        started = time.perf_counter()
        attempt_log = _AttemptLog(api="replicate")
        self._attempt_logs = [attempt_log]

        params = {**T2V_YOUTUBE_PARAMS, **(t2v_params or {})}

        result = self._retry_with_backoff(
            lambda: self._generate_replicate(
                bundle["prompt"],
                image_url=None,  # T2V puro — sem imagem de referência
                params=params,
                negative_prompt=bundle.get("negative_prompt"),
            ),
            attempt_log,
        )

        local_path = result.local_path
        if download and result.video_url:
            downloaded = self._download_video(result.video_url, "replicate_youtube")
            if downloaded:
                local_path = str(downloaded)

        return {
            "video_url": result.video_url,
            "api_used": "replicate",
            "credits_remaining": None,
            "duration_seconds": time.perf_counter() - started,
            "resolution": "1024x576",
            "fallback_reason": None,
            "local_path": local_path,
            "scene_tipo": scene_tipo,
            "emotion": emotion,
            "prompt": bundle["prompt"],
        }

    def generate(
        self,
        prompt: str,
        image_url: str | None = None,
        *,
        product_name: str | None = None,
        download: bool = True,
    ) -> dict[str, Any]:
        """
        Gera vídeo com fallback fal.ai → Replicate → Kling Web.

        Args:
            prompt: Descrição do vídeo (inglês recomendado).
            image_url: URL opcional para image-to-video.
            product_name: Nome do produto para template e-commerce.
            download: Se True, baixa vídeos HTTP para output_dir.

        Returns:
            Dict com video_url, api_used, credits_remaining, duration_seconds,
            resolution, fallback_reason e opcionalmente local_path.

        Raises:
            RuntimeError: Se todas as APIs falharem após retries.
        """
        self._attempt_logs.clear()
        fallback_reason: str | None = None
        started = time.perf_counter()

        providers: list[tuple[str, Callable[[PromptBundle], VideoGenerationResult]]] = [
            ("falai", lambda bundle: self._generate_falai(bundle["prompt"], image_url)),
            (
                "replicate",
                lambda bundle: self._generate_replicate(bundle["prompt"], image_url),
            ),
            ("kling_web", lambda bundle: self._generate_kling_web_sync(bundle)),
        ]

        last_error = "nenhuma API tentada"
        for index, (api_name, generator_fn) in enumerate(providers):
            bundle = build_from_description(
                prompt,
                api_name,  # type: ignore[arg-type]
                product_name=product_name,
            )
            attempt_log = _AttemptLog(api=api_name)
            self._attempt_logs.append(attempt_log)
            api_started = time.perf_counter()

            try:
                result = self._retry_with_backoff(
                    lambda: generator_fn(bundle),
                    attempt_log,
                )
                attempt_log.elapsed_seconds = time.perf_counter() - api_started

                local_path = result.local_path
                if download and result.video_url:
                    downloaded = self._download_video(result.video_url, api_name)
                    if downloaded:
                        local_path = str(downloaded)

                result = VideoGenerationResult(
                    video_url=result.video_url,
                    api_used=result.api_used,
                    credits_remaining=result.credits_remaining,
                    duration_seconds=time.perf_counter() - started,
                    resolution=result.resolution,
                    fallback_reason=fallback_reason,
                    local_path=local_path,
                )

                logger.info(
                    "Vídeo gerado via %s (%s) em %.1fs",
                    api_name,
                    result.resolution,
                    attempt_log.elapsed_seconds,
                )
                return result.to_dict()

            except Exception as error:
                attempt_log.elapsed_seconds = time.perf_counter() - api_started
                last_error = _redact_message(str(error))
                attempt_log.errors.append(last_error)
                logger.warning(
                    "API %s falhou após %d tentativas: %s",
                    api_name,
                    attempt_log.attempts,
                    last_error,
                )
                if index < len(providers) - 1:
                    next_api = providers[index + 1][0]
                    fallback_reason = (
                        f"{api_name} falhou ({last_error}) → tentando {next_api}"
                    )
                    logger.info("Fallback: %s", fallback_reason)

        raise RuntimeError(
            f"Todas as APIs de vídeo falharam. Último erro: {last_error}. "
            f"Logs: {self.get_attempt_summary()}"
        )

    def get_attempt_summary(self) -> list[dict[str, Any]]:
        """Retorna resumo das tentativas por API para relatórios de teste."""
        return [
            {
                "api": log.api,
                "attempts": log.attempts,
                "elapsed_seconds": round(log.elapsed_seconds, 2),
                "errors": log.errors,
            }
            for log in self._attempt_logs
        ]

    # ------------------------------------------------------------------
    # Retry
    # ------------------------------------------------------------------

    def _retry_with_backoff(
        self,
        fn: Callable[[], VideoGenerationResult],
        attempt_log: _AttemptLog,
    ) -> VideoGenerationResult:
        """Executa fn com retries e backoff exponencial."""
        last_error: Exception | None = None

        for attempt in range(1, VIDEO_MAX_RETRIES + 1):
            attempt_log.attempts = attempt
            try:
                return fn()
            except Exception as error:
                last_error = error
                attempt_log.errors.append(_redact_message(str(error)))
                logger.debug(
                    "Tentativa %d/%d falhou: %s",
                    attempt,
                    VIDEO_MAX_RETRIES,
                    _redact_message(str(error)),
                )

                if isinstance(error, (NoCreditError, CaptchaError, ElementNotFoundError)):
                    break

                if attempt < VIDEO_MAX_RETRIES:
                    delay = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                    if self._is_rate_limit_error(error):
                        delay = max(delay, 30.0)
                        logger.info("Rate limit — aguardando %.0fs", delay)
                    time.sleep(delay)

        raise RuntimeError(str(last_error) if last_error else "falha desconhecida")

    @staticmethod
    def _is_rate_limit_error(error: Exception) -> bool:
        """Detecta erros de rate limit para espera prolongada."""
        message = str(error).lower()
        return any(
            token in message
            for token in ("429", "rate limit", "too many requests", "402", "credits")
        )

    # ------------------------------------------------------------------
    # fal.ai via HF Router (primário)
    # ------------------------------------------------------------------

    def _generate_falai(self, prompt: str, image_url: str | None) -> VideoGenerationResult:
        """
        POST para HF Router → fal-ai Wan2.2 5B (text-to-video ou image-to-video).

        Poll assíncrono (202) até timeout VIDEO_TIMEOUT.
        """
        token = os.getenv("HF_API_TOKEN") or os.getenv("HF_TOKEN", "")
        if not token:
            raise RuntimeError("HF_API_TOKEN ausente — configure em .env")

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        route = FALAI_HF_ROUTE_I2V if image_url else FALAI_HF_ROUTE_T2V

        payload: dict[str, Any] = {
            "prompt": prompt,
            "num_frames": 49,
            "aspect_ratio": "16:9",
        }
        if image_url:
            payload["image_url"] = image_url

        started = time.perf_counter()

        video_ref = self._poll_async_http(
            method="POST",
            url=route,
            headers=headers,
            json_body=payload,
            api_label="falai",
        )

        return VideoGenerationResult(
            video_url=video_ref,
            api_used="falai",
            credits_remaining=None,
            duration_seconds=time.perf_counter() - started,
            resolution="480p",
        )

    # ------------------------------------------------------------------
    # Replicate (secundário)
    # ------------------------------------------------------------------

    def _generate_replicate(
        self,
        prompt: str,
        image_url: str | None,
        *,
        params: dict[str, Any] | None = None,
        negative_prompt: str | None = None,
    ) -> VideoGenerationResult:
        """
        POST Replicate predictions com lightricks/ltx-video.

        Poll GET /v1/predictions/{id} até status succeeded.
        """
        token = os.getenv("REPLICATE_API_TOKEN", "")
        if not token:
            raise RuntimeError("REPLICATE_API_TOKEN ausente — configure em .env")

        headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
        }

        is_i2v = bool(image_url)
        i2v_params = {**I2V_OPTIMAL_PARAMS, **(params or {})}

        model_input: dict[str, Any] = {
            "prompt": prompt,
            "negative_prompt": negative_prompt or (
                "blurry, distorted, low quality, watermark, overexposed, shaky camera, text overlay"
            ),
            "length": i2v_params.get("length", 97),
            "steps": i2v_params.get("steps", 30),
            "cfg": i2v_params.get("cfg", 7.5),
        }

        if is_i2v:
            model_input["image"] = image_url
            model_input["target_size"] = i2v_params.get("target_size", 832)
            model_input["image_noise_scale"] = i2v_params.get("image_noise_scale", 0.12)
            resolution = I2V_RESOLUTION
        else:
            t2v_params = {**T2V_YOUTUBE_PARAMS, **(params or {})}
            model_input["target_size"] = t2v_params.get("target_size", 832)
            model_input["aspect_ratio"] = t2v_params.get("aspect_ratio", "16:9")
            model_input["length"] = t2v_params.get("length", 97)
            model_input["steps"] = t2v_params.get("steps", 45)
            model_input["cfg"] = t2v_params.get("cfg", 8.5)
            resolution = "1024x576"

        started = time.perf_counter()
        create_response = self._session.post(
            REPLICATE_PREDICTIONS_URL,
            headers=headers,
            json={"version": REPLICATE_VERSION, "input": model_input},
            timeout=60,
        )
        self._raise_replicate_http_error(create_response)

        prediction = create_response.json()
        prediction_id = prediction.get("id")
        if not prediction_id:
            raise RuntimeError(f"Replicate não retornou prediction id: {prediction}")

        video_url = self._poll_replicate_prediction(prediction_id, headers)
        return VideoGenerationResult(
            video_url=video_url,
            api_used="replicate",
            credits_remaining=None,
            duration_seconds=time.perf_counter() - started,
            resolution=resolution,
        )

    def _poll_replicate_prediction(
        self,
        prediction_id: str,
        headers: dict[str, str],
    ) -> str:
        """Poll prediction Replicate até succeeded ou timeout."""
        status_url = f"{REPLICATE_PREDICTIONS_URL}/{prediction_id}"
        deadline = time.time() + VIDEO_TIMEOUT

        while time.time() < deadline:
            response = self._session.get(status_url, headers=headers, timeout=30)
            self._raise_replicate_http_error(response)
            body = response.json()
            status = body.get("status", "")

            if status == "succeeded":
                output = body.get("output")
                url = self._extract_replicate_output_url(output)
                if url:
                    return url
                raise RuntimeError(f"Replicate succeeded sem URL: {body}")

            if status in ("failed", "canceled"):
                detail = body.get("error", "unknown")
                raise RuntimeError(f"Replicate {status}: {detail}")

            time.sleep(VIDEO_POLL_INTERVAL)

        raise TimeoutError(
            f"Replicate polling timeout após {VIDEO_TIMEOUT}s (id={prediction_id})"
        )

    @staticmethod
    def _extract_replicate_output_url(output: Any) -> str | None:
        """Extrai URL de vídeo do campo output Replicate."""
        if isinstance(output, str) and output.startswith("http"):
            return output
        if isinstance(output, list) and output:
            first = output[0]
            if isinstance(first, str) and first.startswith("http"):
                return first
        return None

    @staticmethod
    def _raise_replicate_http_error(response: requests.Response) -> None:
        """Converte erros HTTP Replicate."""
        if response.status_code == 401:
            raise RuntimeError("Replicate auth failed (401)")
        if response.status_code == 402:
            raise NoCreditError("Replicate créditos esgotados (402)")
        if response.status_code == 429:
            raise RuntimeError("Replicate rate limit (429)")
        if response.status_code >= 400:
            raise RuntimeError(
                f"Replicate HTTP {response.status_code}: {response.text[:400]}"
            )

    # ------------------------------------------------------------------
    # Kling Web Playwright (fallback)
    # ------------------------------------------------------------------

    def _generate_kling_web_sync(self, bundle: PromptBundle) -> VideoGenerationResult:
        """Wrapper síncrono para automação async Kling Web."""
        return asyncio.run(self._generate_kling_web(bundle))

    async def _generate_kling_web(self, bundle: PromptBundle) -> VideoGenerationResult:
        """
        Automação Playwright no app Kling (66 créditos/dia free).

        Fluxo: app/video/new → login → preencher prompt → Generate → download MP4.
        """
        email, password = _kling_web_credentials()
        if not email or not password:
            raise RuntimeError(
                "KLING_EMAIL/KLING_PASSWORD ausentes para fallback Playwright"
            )

        try:
            from playwright.async_api import async_playwright
        except ImportError as error:
            raise RuntimeError(
                "playwright não instalado — pip install playwright && playwright install chromium"
            ) from error

        started = time.perf_counter()
        output_dir = Path(os.getenv("VIDEO_OUTPUT_DIR", str(self._output_dir)))
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / f"kling_{int(time.time())}.mp4"
        headful = _kling_headful()
        debug = _kling_debug_enabled()

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=not headful,
                slow_mo=500 if headful else 0,
            )
            context = await browser.new_context(
                accept_downloads=True,
                viewport={"width": 1440, "height": 900},
                locale="en-US",
            )
            page = await context.new_page()

            try:
                await page.goto(
                    f"{KLING_APP_BASE}{KLING_VIDEO_NEW_PATH}",
                    wait_until="domcontentloaded",
                    timeout=KLING_LOGIN_TIMEOUT,
                )
                await page.wait_for_timeout(4000)
                if debug:
                    await _kling_debug_screenshot(page, "01_video_new")

                await self._kling_dismiss_blocking_ui(page)
                if debug:
                    await _kling_debug_screenshot(page, "02_after_dismiss")

                if await self._kling_needs_login(page):
                    await self._kling_web_login(page, email, password, debug=debug)
                else:
                    logger.info("Kling: sessão já autenticada ou login não necessário")

                if debug:
                    await _kling_debug_screenshot(page, "03_after_login")

                await self._kling_web_submit(page, bundle, debug=debug)
                if debug:
                    await _kling_debug_screenshot(page, "04_after_submit")

                await self._kling_web_wait_and_download(page, target, debug=debug)
                if debug:
                    await _kling_debug_screenshot(page, "05_after_download")
            finally:
                if headful:
                    await page.wait_for_timeout(2000)
                await context.close()
                await browser.close()

        if not target.exists():
            raise RuntimeError("Kling Web não produziu arquivo MP4")

        return VideoGenerationResult(
            video_url=target.as_uri(),
            api_used="kling_web",
            credits_remaining=None,
            duration_seconds=time.perf_counter() - started,
            resolution="720p",
            local_path=str(target),
        )

    async def _kling_dismiss_blocking_ui(self, page: Any) -> None:
        """Dispensa cookies e modais promocionais que bloqueiam cliques."""
        await self._kling_dismiss_cookies(page)
        for _ in range(3):
            closed = False
            for selector in KLING_PROMO_CLOSE_SELECTORS:
                locator = page.locator(selector)
                if await locator.count():
                    try:
                        await locator.first.click(timeout=3000, force=True)
                        await page.wait_for_timeout(800)
                        closed = True
                        break
                    except Exception:
                        continue
            if not closed:
                try:
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(400)
                except Exception:
                    pass
            if await page.locator(".el-overlay:visible").count() == 0:
                break

    async def _kling_dismiss_cookies(self, page: Any) -> None:
        """Aceita banner de cookies/LGPD se presente."""
        for selector in KLING_COOKIE_SELECTORS:
            locator = page.locator(selector)
            if await locator.count() and await locator.first.is_visible():
                try:
                    await locator.first.click(timeout=3000)
                    await page.wait_for_timeout(800)
                    logger.debug("Kling: cookies dispensados via %s", selector)
                    return
                except Exception:
                    continue

    @staticmethod
    async def _kling_find_visible(
        page: Any,
        selectors: tuple[str, ...] | list[str],
        *,
        timeout: int = KLING_SELECTOR_TIMEOUT,
    ) -> Any:
        """Tenta múltiplos seletores até encontrar elemento visível."""
        per_selector = max(3000, timeout // max(len(selectors), 1))
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                await locator.wait_for(state="visible", timeout=per_selector)
                return locator
            except Exception:
                continue
        raise ElementNotFoundError(f"Nenhum seletor funcionou: {list(selectors)}")

    @staticmethod
    async def _kling_needs_login(page: Any) -> bool:
        """True se botão One-click Sign In estiver visível."""
        sign_in = page.locator('button:has-text("One-click Sign In")')
        return await sign_in.count() > 0 and await sign_in.first.is_visible()

    async def _kling_web_login(
        self,
        page: Any,
        email: str,
        password: str,
        *,
        debug: bool = False,
    ) -> None:
        """Login via One-click Sign In → Continue with email → Sign In."""
        if await self._page_has_captcha(page):
            raise CaptchaError("CAPTCHA detectado no login Kling")

        sign_in_entry = page.locator('button:has-text("One-click Sign In")')
        if await sign_in_entry.count() and await sign_in_entry.first.is_visible():
            await sign_in_entry.first.click(timeout=KLING_SELECTOR_TIMEOUT, force=True)
            await page.wait_for_timeout(3000)
            if debug:
                await _kling_debug_screenshot(page, "login_modal")

        await self._kling_dismiss_cookies(page)

        email_input = page.locator('input[type="email"]')
        if not (await email_input.count() and await email_input.first.is_visible()):
            welcome = page.get_by_text("Welcome to Kling AI")
            if await welcome.count():
                await welcome.first.wait_for(state="visible", timeout=KLING_SELECTOR_TIMEOUT)

            email_entry = page.locator(
                'div.sign-in-button.mt-24:has-text("Continue with email"), '
                'div.sign-in-button:has-text("Continue with email")'
            )
            if await email_entry.count() == 0:
                email_entry = page.get_by_text("Continue with email", exact=True)
            await email_entry.first.click(timeout=KLING_SELECTOR_TIMEOUT, force=True)
            await page.wait_for_timeout(2000)
            if debug:
                await _kling_debug_screenshot(page, "email_form")

        email_field = await self._kling_find_visible(page, KLING_EMAIL_SELECTORS)
        await email_field.fill(email, timeout=KLING_SELECTOR_TIMEOUT)

        password_field = await self._kling_find_visible(page, KLING_PASSWORD_SELECTORS)
        await password_field.fill(password, timeout=KLING_SELECTOR_TIMEOUT)
        if debug:
            await _kling_debug_screenshot(page, "password_filled")

        sign_in_btn = page.locator(
            'button:has-text("Sign In"):not([disabled]), '
            'button:has-text("Sign In"), '
            '.generic-button:has-text("Sign In")'
        )
        if await sign_in_btn.count():
            await sign_in_btn.first.click(timeout=KLING_SELECTOR_TIMEOUT, force=True)
        else:
            await page.keyboard.press("Enter")

        await page.wait_for_timeout(5000)

        if await page.locator('input[type="email"]').count():
            if await page.locator('input[type="email"]').first.is_visible():
                welcome_visible = (
                    await page.get_by_text("Welcome to Kling AI").count()
                    and await page.get_by_text("Welcome to Kling AI").first.is_visible()
                )
                if welcome_visible:
                    raise RuntimeError(
                        "Login Kling falhou — modal de autenticação ainda visível. "
                        "Verifique KLING_EMAIL/KLING_PASSWORD."
                    )

    async def _kling_web_submit(
        self,
        page: Any,
        bundle: PromptBundle,
        *,
        debug: bool = False,
    ) -> None:
        """Preenche prompt e dispara geração na página de vídeo."""
        if await self._page_has_captcha(page):
            raise CaptchaError("CAPTCHA detectado antes da geração")

        prompt_selectors = (
            "textarea",
            'textarea[placeholder*="prompt" i]',
            'textarea[placeholder*="describe" i]',
            '[contenteditable="true"]',
        )
        prompt_box = await self._kling_find_visible(page, prompt_selectors)
        await prompt_box.fill(bundle["prompt"], timeout=KLING_SELECTOR_TIMEOUT)

        if bundle.get("negative_prompt"):
            negative = page.locator(
                'textarea[name*="negative"], textarea[placeholder*="negative" i]'
            )
            if await negative.count() and await negative.first.is_visible():
                await negative.first.fill(bundle["negative_prompt"], timeout=10_000)

        generate_btn = page.locator(
            'button:has-text("Generate"), button.button-pay:has-text("Generate")'
        )
        if await generate_btn.count() == 0:
            generate_btn = page.get_by_role("button", name=re.compile(r"generate", re.I))
        await generate_btn.first.click(timeout=KLING_SELECTOR_TIMEOUT, force=True)

    async def _kling_web_wait_and_download(
        self,
        page: Any,
        target: Path,
        *,
        debug: bool = False,
    ) -> None:
        """Aguarda conclusão e baixa MP4."""
        deadline = time.time() + KLING_WEB_TIMEOUT

        while time.time() < deadline:
            if await self._page_has_captcha(page):
                raise CaptchaError("CAPTCHA detectado durante geração")

            body_text = (await page.content()).lower()
            if any(
                phrase in body_text
                for phrase in ("no credits", "insufficient credits", "out of credits")
            ):
                raise NoCreditError("Créditos Kling web esgotados")

            download_btn = page.get_by_role("button", name=re.compile(r"download", re.I))
            if await download_btn.count() > 0:
                async with page.expect_download(timeout=60_000) as download_info:
                    await download_btn.first.click()
                download = await download_info.value
                await download.save_as(str(target))
                return

            await asyncio.sleep(VIDEO_POLL_INTERVAL)

        raise TimeoutError(f"Kling Web timeout após {KLING_WEB_TIMEOUT}s")

    @staticmethod
    async def _page_has_captcha(page: Any) -> bool:
        """Heurística simples para detectar CAPTCHA."""
        captcha = page.locator(
            'iframe[src*="captcha"], div[class*="captcha"], #captcha, [data-captcha]'
        )
        return await captcha.count() > 0

    # ------------------------------------------------------------------
    # Poll genérico (fal.ai / HF Router)
    # ------------------------------------------------------------------

    def _poll_async_http(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str],
        json_body: dict[str, Any] | None = None,
        api_label: str,
    ) -> str:
        """Executa request e faz poll se resposta for assíncrona (202)."""
        deadline = time.time() + VIDEO_TIMEOUT
        poll_url = url
        first = True

        while time.time() < deadline:
            if first:
                response = self._session.request(
                    method,
                    poll_url,
                    headers=headers,
                    json=json_body,
                    timeout=int(VIDEO_TIMEOUT),
                )
                first = False
            else:
                response = self._session.get(
                    poll_url,
                    headers=headers,
                    timeout=int(VIDEO_TIMEOUT),
                )

            if response.status_code == 429:
                raise RuntimeError(f"{api_label} rate limit (429)")
            if response.status_code == 402:
                raise NoCreditError(
                    f"{api_label} créditos HF esgotados (402) — adicione créditos ou configure REPLICATE_API_TOKEN"
                )
            if response.status_code >= 400 and response.status_code not in (202,):
                raise RuntimeError(
                    f"{api_label} HTTP {response.status_code}: {response.text[:400]}"
                )

            content_type = response.headers.get("Content-Type", "")
            if "video" in content_type or (
                response.content[:4] == b"\x00\x00\x00\x18"
                or response.content[:4] == b"\x00\x00\x00\x20"
            ):
                saved = self._save_temp_video(response.content, api_label)
                return saved.as_uri()

            try:
                data = response.json()
            except json.JSONDecodeError:
                if len(response.content) > 1000:
                    saved = self._save_temp_video(response.content, api_label)
                    return saved.as_uri()
                raise RuntimeError(f"{api_label} resposta inválida")

            video_url = self._extract_video_url_from_json(data)
            if video_url:
                return video_url

            status = str(data.get("status", "")).lower()
            if status in ("succeeded", "completed", "complete", "success"):
                raise RuntimeError(f"{api_label} status ok sem URL: {str(data)[:300]}")

            if status in ("failed", "error"):
                raise RuntimeError(f"{api_label} falhou: {data.get('error', data)}")

            poll_url = (
                data.get("status_url")
                or data.get("url")
                or response.headers.get("Location")
                or poll_url
            )

            if response.status_code != 202 and status not in (
                "processing",
                "in_progress",
                "queued",
                "pending",
                "starting",
            ):
                raise RuntimeError(
                    f"{api_label} sem URL de vídeo: {str(data)[:300]}"
                )

            time.sleep(VIDEO_POLL_INTERVAL)

        raise TimeoutError(f"{api_label} polling timeout após {VIDEO_TIMEOUT}s")

    @staticmethod
    def _extract_video_url_from_json(data: Any) -> str | None:
        """Extrai URL de vídeo de respostas JSON heterogêneas."""
        if isinstance(data, dict):
            for key in ("video_url", "url", "output", "video"):
                value = data.get(key)
                if isinstance(value, str) and value.startswith("http"):
                    return value
                if isinstance(value, dict) and isinstance(value.get("url"), str):
                    return value["url"]
            for nested_key in ("data", "output", "result", "videos"):
                nested = data.get(nested_key)
                found = VideoGenerator._extract_video_url_from_json(nested)
                if found:
                    return found
        elif isinstance(data, list) and data:
            return VideoGenerator._extract_video_url_from_json(data[0])
        return None

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    def _download_video(self, video_url: str, api_name: str) -> Path | None:
        """Baixa vídeo de URL HTTP para output_dir."""
        parsed = urlparse(video_url)
        if parsed.scheme == "file":
            return Path(parsed.path)

        self._output_dir.mkdir(parents=True, exist_ok=True)
        target = self._output_dir / f"video_{api_name}_{int(time.time())}.mp4"

        try:
            response = self._session.get(video_url, timeout=120, stream=True)
            response.raise_for_status()
            with target.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=8192):
                    handle.write(chunk)
            return target
        except requests.RequestException as error:
            logger.warning("Download falhou: %s", _redact_message(str(error)))
            return None

    def _save_temp_video(self, content: bytes, prefix: str) -> Path:
        """Salva bytes de vídeo em arquivo temporário."""
        temp_dir = self._output_dir / "temp_videos"
        temp_dir.mkdir(parents=True, exist_ok=True)
        path = temp_dir / f"{prefix}_{int(time.time())}.mp4"
        path.write_bytes(content)
        return path


def _kling_web_credentials() -> tuple[str, str]:
    """Retorna credenciais Kling web com fallback LUMA_*."""
    email = os.getenv("KLING_EMAIL") or os.getenv("LUMA_EMAIL", "")
    password = os.getenv("KLING_PASSWORD") or os.getenv("LUMA_PASSWORD", "")
    return email, password


def _kling_headful() -> bool:
    """True para Playwright visível (debug manual)."""
    return os.getenv("KLING_HEADFUL", "").lower() in {"1", "true", "yes"}


def _kling_debug_enabled() -> bool:
    """True para salvar screenshots em debug/ durante automação Kling."""
    return os.getenv("KLING_DEBUG", "").lower() in {"1", "true", "yes"}


async def _kling_debug_screenshot(page: Any, name: str) -> Path | None:
    """Salva screenshot de debug se KLING_DEBUG estiver ativo."""
    if not _kling_debug_enabled():
        return None
    debug_dir = Path("debug")
    debug_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(debug_dir.glob("kling_login_*.png"))
    step = len(existing) + 1
    path = debug_dir / f"kling_login_{step:02d}_{name}.png"
    await page.screenshot(path=str(path), full_page=True)
    logger.debug("Kling debug screenshot: %s", path)
    return path


def falai_is_configured() -> bool:
    """True se HF_API_TOKEN está presente."""
    return bool(os.getenv("HF_API_TOKEN") or os.getenv("HF_TOKEN"))


def replicate_is_configured() -> bool:
    """True se REPLICATE_API_TOKEN está presente."""
    return bool(os.getenv("REPLICATE_API_TOKEN"))


def kling_web_is_configured() -> bool:
    """True se credenciais Kling web estão presentes."""
    email, password = _kling_web_credentials()
    return bool(email and password)


def _probe_video_metrics(path: Path) -> dict[str, Any]:
    """Extrai duração e resolução via ffprobe (se disponível)."""
    import shutil
    import subprocess

    metrics: dict[str, Any] = {"duration_s": None, "width": None, "height": None, "size_bytes": None}
    if not path.exists():
        return metrics

    metrics["size_bytes"] = path.stat().st_size
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return metrics

    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,duration",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        stream = (data.get("streams") or [{}])[0]
        metrics["width"] = stream.get("width")
        metrics["height"] = stream.get("height")
        duration = stream.get("duration")
        metrics["duration_s"] = round(float(duration), 2) if duration else None
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError, TypeError):
        pass

    return metrics


def write_cli_test_report(result: dict[str, Any], output_path: Path, metrics: dict[str, Any]) -> Path:
    """Atualiza analysis/test_results.md após geração CLI bem-sucedida."""
    report_dir = Path("analysis")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "test_results.md"

    resolution = result.get("resolution", "—")
    if metrics.get("width") and metrics.get("height"):
        resolution = f"{metrics['width']}x{metrics['height']}"

    lines = [
        "# Resultados dos Testes de APIs de Vídeo",
        "",
        f"> Gerado em: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Status",
        "",
        "✅ Primeiro vídeo real gerado com sucesso via CLI.",
        "",
        "## Configuração detectada",
        "",
        "| API | Configurada |",
        "|-----|-------------|",
        f"| fal.ai (HF) | {'✅' if falai_is_configured() else '❌'} |",
        f"| Replicate | {'✅' if replicate_is_configured() else '❌'} |",
        f"| Kling Web | {'✅' if kling_web_is_configured() else '❌'} |",
        "",
        "## Resultado do teste real (CLI)",
        "",
        "| Métrica | Valor |",
        "|---------|-------|",
        f"| API usada | `{result.get('api_used', '—')}` |",
        f"| Tempo total (s) | {round(result.get('duration_seconds', 0), 2)} |",
        f"| Resolução | {resolution} |",
        f"| Duração vídeo (s) | {metrics.get('duration_s', '—')} |",
        f"| Tamanho (bytes) | {metrics.get('size_bytes', '—')} |",
        f"| Créditos restantes | {result.get('credits_remaining', '—')} |",
        f"| Fallback | {result.get('fallback_reason') or '—'} |",
        f"| Arquivo | `{output_path}` |",
        "",
        "## Comando executado",
        "",
        "```bash",
        "python -m src.video_generator \\",
        '  --prompt "sneaker product shot, studio lighting, slow zoom" \\',
        "  --output ./output/videos/test_real.mp4",
        "```",
        "",
        "## Vídeos gerados",
        "",
        f"- **test_real**: ✅ `{output_path}`",
        "",
        "## Observações",
        "",
        "1. APIs free entregam ~480p; use `src.video_upscaler.upscale_video()` para 960p+.",
        "2. Configure `REPLICATE_API_TOKEN` e `KLING_EMAIL`/`KLING_PASSWORD` para fallback automático.",
        "3. Testes unitários: `pytest tests/test_video_apis.py -v -m \"not integration\"`.",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> int:
    """CLI standalone para geração de vídeo real."""
    import argparse
    import shutil

    parser = argparse.ArgumentParser(description="Gera vídeo via APIs free com fallback automático.")
    parser.add_argument("--prompt", required=True, help="Descrição do vídeo (inglês recomendado)")
    parser.add_argument(
        "--output",
        default="./output/videos/test_real.mp4",
        help="Caminho do MP4 de saída",
    )
    parser.add_argument("--image-url", default=None, help="URL opcional para image-to-video")
    parser.add_argument("--product-name", default=None, help="Nome do produto para template e-commerce")
    parser.add_argument("--no-report", action="store_true", help="Não atualizar analysis/test_results.md")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generator = VideoGenerator(output_dir=output_path.parent)
    started = time.perf_counter()

    try:
        result = generator.generate(
            prompt=args.prompt,
            image_url=args.image_url,
            product_name=args.product_name,
            download=True,
        )
    except RuntimeError as error:
        logger.error("Geração falhou: %s", _redact_message(str(error)))
        safe_error = _redact_message(str(error)).encode("ascii", errors="replace").decode("ascii")
        print(f"[ERRO] Falha: {safe_error}")
        return 1

    local_path = result.get("local_path")
    if local_path and Path(local_path).exists():
        src = Path(local_path)
        if src.resolve() != output_path.resolve():
            shutil.copy2(src, output_path)
            result["local_path"] = str(output_path)
    elif result.get("video_url", "").startswith(("http://", "https://")):
        downloaded = generator._download_video(result["video_url"], result.get("api_used", "cli"))
        if downloaded:
            shutil.copy2(downloaded, output_path)
            result["local_path"] = str(output_path)

    if not output_path.exists() or output_path.stat().st_size < 5000:
        print("[ERRO] Video nao salvo ou arquivo invalido.")
        return 1

    metrics = _probe_video_metrics(output_path)
    elapsed = time.perf_counter() - started

    print(f"[OK] Video gerado: {output_path}")
    print(f"   API: {result.get('api_used')}")
    print(f"   Resolução: {result.get('resolution')}")
    print(f"   Tempo: {elapsed:.1f}s")
    if result.get("fallback_reason"):
        reason = result["fallback_reason"].encode("ascii", errors="replace").decode("ascii")
        print(f"   Fallback: {reason}")

    if not args.no_report:
        report = write_cli_test_report(result, output_path, metrics)
        print(f"   Relatório: {report}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
