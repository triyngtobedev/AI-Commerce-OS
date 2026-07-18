"""
VideoGenerator — geração de vídeo com fallback automático.

Ordem de fallback (grátis → premium → backup):
  Kling Web (Playwright, grátis) → fal.ai Kling 2.6 Pro → Replicate Wan 2.6 → fal.ai Wan (HF Router)

Variáveis de ambiente:
    KLING_EMAIL           — E-mail Kling web (tier grátis — 66 créditos/dia)
    KLING_PASSWORD        — Senha Kling web
    FAL_KEY               — Chave fal.ai (Kling 2.6 Pro premium)
    REPLICATE_API_TOKEN   — Token Replicate (Wan 2.6 T2V/I2V)
    REPLICATE_MODEL       — Modelo T2V (default: wan-video/wan-2.6-t2v)
    REPLICATE_I2V_MODEL   — Modelo I2V (default: wan-video/wan-2.6-i2v)
    HF_API_TOKEN          — Token Hugging Face (router fal-ai Wan2.2, último fallback)
    VIDEO_OUTPUT_DIR      — Diretório de saída (default: ./output/videos)
    VIDEO_MAX_RETRIES     — Tentativas por API (default: 3)
    VIDEO_POLL_INTERVAL   — Intervalo de poll em segundos (default: 10)
    VIDEO_TIMEOUT         — Timeout de geração/poll em segundos (default: 300)
    FAL_KLING_DURATION    — Duração Kling fal.ai: 5 ou 10 (default: 5)
    FAL_KLING_AUDIO       — true/false — áudio nativo Kling (default: false)
    REPLICATE_WAN_RESOLUTION — 720p ou 1080p (default: 720p, mais econômico)
    REPLICATE_WAN_DURATION   — Segundos Wan no Replicate (default: 5)
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
REPLICATE_MODEL = os.getenv("REPLICATE_MODEL", "wan-video/wan-2.6-t2v")
REPLICATE_I2V_MODEL = os.getenv("REPLICATE_I2V_MODEL", "wan-video/wan-2.6-i2v")
REPLICATE_LTX_VERSION = os.getenv(
    "REPLICATE_LTX_VERSION",
    "8c47da666861d081eeb4d1261853087de23923a268a69b63febdf5dc1dee08e4",
)
FAL_QUEUE_BASE = "https://queue.fal.run"
FAL_KLING_T2V_MODEL = os.getenv(
    "FAL_KLING_T2V_MODEL",
    "fal-ai/kling-video/v2.6/pro/text-to-video",
)
FAL_KLING_I2V_MODEL = os.getenv(
    "FAL_KLING_I2V_MODEL",
    "fal-ai/kling-video/v2.6/pro/image-to-video",
)
FAL_KLING_DURATION = os.getenv("FAL_KLING_DURATION", "5")
FAL_KLING_GENERATE_AUDIO = os.getenv("FAL_KLING_AUDIO", "false").lower() in {"1", "true", "yes"}
REPLICATE_WAN_RESOLUTION = os.getenv("REPLICATE_WAN_RESOLUTION", "720p")
REPLICATE_WAN_DURATION = int(os.getenv("REPLICATE_WAN_DURATION", "5"))
FAL_KLING_ESTIMATED_COST_USD = float(os.getenv("FAL_KLING_ESTIMATED_COST_USD", "0.35"))
REPLICATE_WAN_ESTIMATED_COST_USD = float(os.getenv("REPLICATE_WAN_ESTIMATED_COST_USD", "0.25"))
KLING_APP_BASE = os.getenv("KLING_APP_BASE", "https://kling.ai")
KLING_VIDEO_NEW_PATH = "/app/video/new"
KLING_SELECTOR_TIMEOUT = int(os.getenv("KLING_SELECTOR_TIMEOUT", "20000"))
KLING_LOGIN_TIMEOUT = int(os.getenv("KLING_LOGIN_TIMEOUT", "30000"))
KLING_STORAGE_STATE = Path(os.getenv("KLING_STORAGE_STATE", "./cache/kling_storage_state.json"))
KLING_EMAIL_ENTRY_SELECTORS = (
    'div.sign-in-button.mt-24:has-text("Sign in with email")',
    'div.sign-in-button:has-text("Sign in with email")',
    'div.sign-in-button.mt-24:has-text("Continue with email")',
    'div.sign-in-button:has-text("Continue with email")',
    'div.sign-in-button.mt-24',
    'div.sign-in-button',
)
KLING_LOGIN_PATHS = (
    "/global/account/login",
    "/account/login",
    "/login",
)
KLING_CHAT_DISMISS_SELECTORS = (
    'button:has-text("End Chat")',
    'button:has-text("Cancel")',
)

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
        "FAL_KEY",
        "FAL_API_KEY",
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

    Ordem: Kling Web (grátis) → fal.ai Kling 2.6 Pro → Replicate Wan 2.6 → HF Router Wan2.2
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
        Fluxo de produção I2V e-commerce: prompt otimizado → fal Kling / Replicate Wan → upscale 2x.

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
        self._attempt_logs.clear()
        negative = bundle.get("negative_prompt")

        result_dict = self._generate_with_fallback(
            prompt=bundle["prompt"],
            image_url=image_url,
            negative_prompt=negative,
            download=download,
            started=started,
            i2v_params=replicate_params,
        )

        local_path = result_dict.get("local_path")
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
            "video_url": result_dict["video_url"],
            "api_used": result_dict["api_used"],
            "credits_remaining": None,
            "duration_seconds": result_dict["duration_seconds"],
            "resolution": resolution,
            "fallback_reason": result_dict.get("fallback_reason"),
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
        Gera vídeo T2V para cenas documentais YouTube Dark.

        Cadeia: Kling Web (grátis) → fal Kling 2.6 Pro → Replicate Wan 2.6 → HF Wan2.2.

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
        params = {**T2V_YOUTUBE_PARAMS, **(t2v_params or {})}

        result_dict = self._generate_with_fallback(
            prompt=bundle["prompt"],
            image_url=None,
            negative_prompt=bundle.get("negative_prompt"),
            download=download,
            started=started,
            replicate_params=params,
            scene_mode=True,
        )

        return {
            "video_url": result_dict["video_url"],
            "api_used": result_dict["api_used"],
            "credits_remaining": None,
            "duration_seconds": result_dict["duration_seconds"],
            "resolution": result_dict.get("resolution", "1280x720"),
            "fallback_reason": result_dict.get("fallback_reason"),
            "local_path": result_dict.get("local_path"),
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
        Gera vídeo com fallback Kling Web → fal Kling 2.6 → Replicate Wan → HF Wan2.2.

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
        started = time.perf_counter()

        return self._generate_with_fallback(
            prompt=prompt,
            image_url=image_url,
            product_name=product_name,
            download=download,
            started=started,
        )

    def _generate_with_fallback(
        self,
        *,
        prompt: str,
        image_url: str | None = None,
        product_name: str | None = None,
        negative_prompt: str | None = None,
        download: bool = True,
        started: float | None = None,
        replicate_params: dict[str, Any] | None = None,
        i2v_params: dict[str, Any] | None = None,
        scene_mode: bool = False,
    ) -> dict[str, Any]:
        """Executa cadeia de providers até sucesso ou esgotar tentativas."""
        from src.prompt_builder import _inline_negative

        started = started or time.perf_counter()
        fallback_reason: str | None = None
        providers = self._provider_chain(image_url=image_url)

        if not providers:
            raise RuntimeError(
                "Nenhuma API de vídeo configurada. Defina KLING_EMAIL/PASSWORD, "
                "FAL_KEY, REPLICATE_API_TOKEN ou HF_API_TOKEN."
            )

        last_error = "nenhuma API tentada"
        for index, api_name in enumerate(providers):
            if api_name == "kling_web":
                bundle = build_from_description(
                    prompt,
                    "kling_web",  # type: ignore[arg-type]
                    product_name=product_name,
                )
                if negative_prompt:
                    bundle = {
                        "prompt": prompt,
                        "negative_prompt": negative_prompt,
                    }
            elif api_name == "falai" and negative_prompt:
                bundle = {
                    "prompt": _inline_negative(prompt, negative_prompt),
                    "negative_prompt": None,
                }
            elif negative_prompt is not None:
                bundle = {"prompt": prompt, "negative_prompt": negative_prompt}
            else:
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
                    lambda api=api_name, b=bundle: self._invoke_provider(
                        api,
                        b,
                        image_url=image_url,
                        replicate_params=replicate_params or i2v_params,
                    ),
                    attempt_log,
                )
                attempt_log.elapsed_seconds = time.perf_counter() - api_started

                local_path = result.local_path
                download_label = f"{api_name}_youtube" if scene_mode else api_name
                if download and result.video_url:
                    downloaded = self._download_video(result.video_url, download_label)
                    if downloaded:
                        local_path = str(downloaded)

                output = VideoGenerationResult(
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
                    output.resolution,
                    attempt_log.elapsed_seconds,
                )
                return output.to_dict()

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
                    next_api = providers[index + 1]
                    fallback_reason = (
                        f"{api_name} falhou ({last_error}) → tentando {next_api}"
                    )
                    logger.info("Fallback: %s", fallback_reason)

        raise RuntimeError(
            f"Todas as APIs de vídeo falharam. Último erro: {last_error}. "
            f"Logs: {self.get_attempt_summary()}"
        )

    @staticmethod
    def _provider_chain(*, image_url: str | None) -> list[str]:
        """Ordem: grátis → premium fal → Replicate → HF Router."""
        chain: list[str] = []
        if kling_web_is_configured() and not image_url:
            chain.append("kling_web")
        if fal_kling_is_configured():
            chain.append("fal_kling")
        if replicate_is_configured():
            chain.append("replicate")
        if falai_is_configured():
            chain.append("falai")
        return chain

    def _invoke_provider(
        self,
        api_name: str,
        bundle: PromptBundle,
        *,
        image_url: str | None,
        replicate_params: dict[str, Any] | None = None,
    ) -> VideoGenerationResult:
        """Despacha geração para o provider indicado."""
        prompt = bundle["prompt"]
        negative = bundle.get("negative_prompt")

        if api_name == "kling_web":
            return self._generate_kling_web_sync(bundle)
        if api_name == "fal_kling":
            return self._generate_fal_kling(
                prompt,
                image_url,
                negative_prompt=negative,
            )
        if api_name == "replicate":
            return self._generate_replicate(
                prompt,
                image_url,
                params=replicate_params,
                negative_prompt=negative,
            )
        if api_name == "falai":
            return self._generate_falai(prompt, image_url)
        raise RuntimeError(f"Provider desconhecido: {api_name}")

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
    # fal.ai Kling 2.6 Pro (premium)
    # ------------------------------------------------------------------

    def _generate_fal_kling(
        self,
        prompt: str,
        image_url: str | None,
        *,
        negative_prompt: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> VideoGenerationResult:
        """
        Gera vídeo via fal.ai Kling 2.6 Pro (T2V ou I2V).

        Usa fila assíncrona queue.fal.run com poll até COMPLETED.
        """
        token = _fal_api_key()
        if not token:
            raise RuntimeError("FAL_KEY ausente — configure em .env")

        is_i2v = bool(image_url)
        model_id = FAL_KLING_I2V_MODEL if is_i2v else FAL_KLING_T2V_MODEL
        merged = params or {}

        payload: dict[str, Any] = {
            "prompt": prompt,
            "duration": str(merged.get("duration", FAL_KLING_DURATION)),
            "aspect_ratio": merged.get("aspect_ratio", "16:9"),
            "negative_prompt": negative_prompt or "blur, distort, and low quality",
            "cfg_scale": merged.get("cfg_scale", 0.5),
            "generate_audio": merged.get("generate_audio", FAL_KLING_GENERATE_AUDIO),
        }
        if is_i2v:
            payload["image_url"] = image_url

        headers = {
            "Authorization": f"Key {token}",
            "Content-Type": "application/json",
        }
        submit_url = f"{FAL_QUEUE_BASE}/{model_id}"
        started = time.perf_counter()

        create_response = self._session.post(
            submit_url,
            headers=headers,
            json=payload,
            timeout=60,
        )
        self._raise_fal_http_error(create_response, "fal_kling")

        body = create_response.json()
        request_id = body.get("request_id")
        if not request_id:
            raise RuntimeError(f"fal Kling não retornou request_id: {body}")

        video_url = self._poll_fal_queue(model_id, request_id, headers)
        resolution = "1280x720" if payload["aspect_ratio"] == "16:9" else "720x1280"
        return VideoGenerationResult(
            video_url=video_url,
            api_used="fal_kling",
            credits_remaining=None,
            duration_seconds=time.perf_counter() - started,
            resolution=resolution,
        )

    def _poll_fal_queue(
        self,
        model_id: str,
        request_id: str,
        headers: dict[str, str],
    ) -> str:
        """Poll fila fal.ai até COMPLETED e extrai URL do vídeo."""
        status_url = f"{FAL_QUEUE_BASE}/{model_id}/requests/{request_id}/status"
        result_url = f"{FAL_QUEUE_BASE}/{model_id}/requests/{request_id}"
        deadline = time.time() + VIDEO_TIMEOUT

        while time.time() < deadline:
            response = self._session.get(status_url, headers=headers, timeout=30)
            self._raise_fal_http_error(response, "fal_kling")
            body = response.json()
            status = str(body.get("status", "")).upper()

            if status == "COMPLETED":
                result_response = self._session.get(result_url, headers=headers, timeout=60)
                self._raise_fal_http_error(result_response, "fal_kling")
                result_body = result_response.json()
                url = self._extract_fal_video_url(result_body)
                if url:
                    return url
                raise RuntimeError(f"fal Kling COMPLETED sem URL: {str(result_body)[:400]}")

            if status in ("FAILED", "CANCELLED", "CANCELED"):
                detail = body.get("error") or body.get("detail") or body
                raise RuntimeError(f"fal Kling {status}: {detail}")

            time.sleep(VIDEO_POLL_INTERVAL)

        raise TimeoutError(
            f"fal Kling polling timeout após {VIDEO_TIMEOUT}s (id={request_id})"
        )

    @staticmethod
    def _extract_fal_video_url(data: Any) -> str | None:
        """Extrai URL de vídeo de respostas fal.ai."""
        if isinstance(data, dict):
            video = data.get("video")
            if isinstance(video, dict) and isinstance(video.get("url"), str):
                return video["url"]
            if isinstance(video, str) and video.startswith("http"):
                return video
            for key in ("video_url", "url", "output"):
                value = data.get(key)
                if isinstance(value, str) and value.startswith("http"):
                    return value
                if isinstance(value, dict) and isinstance(value.get("url"), str):
                    return value["url"]
            nested = data.get("response") or data.get("data") or data.get("output")
            if nested is not None:
                return VideoGenerator._extract_fal_video_url(nested)
        return None

    @staticmethod
    def _raise_fal_http_error(response: requests.Response, api_label: str) -> None:
        """Converte erros HTTP fal.ai."""
        if response.status_code == 401:
            raise RuntimeError(f"{api_label} auth failed (401)")
        if response.status_code in (402, 403):
            raise NoCreditError(f"{api_label} créditos esgotados ({response.status_code})")
        if response.status_code == 429:
            raise RuntimeError(f"{api_label} rate limit (429)")
        if response.status_code >= 400:
            raise RuntimeError(
                f"{api_label} HTTP {response.status_code}: {response.text[:400]}"
            )

    # ------------------------------------------------------------------
    # Replicate (Wan 2.6 — backup pago)
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
        POST Replicate predictions — Wan 2.6 T2V/I2V (default) ou LTX legado.

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
        model_name = REPLICATE_I2V_MODEL if is_i2v else REPLICATE_MODEL
        use_wan = "wan" in model_name.lower()

        if use_wan:
            wan_params = {**(params or {})}
            model_input: dict[str, Any] = {
                "prompt": prompt,
                "negative_prompt": negative_prompt or (
                    "blurry, distorted, low quality, watermark, overexposed, "
                    "shaky camera, text overlay, cartoon"
                ),
                "aspect_ratio": wan_params.get("aspect_ratio", "16:9"),
                "resolution": wan_params.get("resolution", REPLICATE_WAN_RESOLUTION),
                "duration": wan_params.get("duration", REPLICATE_WAN_DURATION),
                "enable_prompt_expansion": wan_params.get("enable_prompt_expansion", True),
            }
            if is_i2v:
                model_input["image"] = image_url
            resolution = (
                "1920x1080"
                if model_input["resolution"] == "1080p"
                else "1280x720"
            )
        else:
            i2v_params = {**I2V_OPTIMAL_PARAMS, **(params or {})}
            model_input = {
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
        if "/" in model_name:
            create_url = f"https://api.replicate.com/v1/models/{model_name}/predictions"
            create_body: dict[str, Any] = {"input": model_input}
        else:
            create_url = REPLICATE_PREDICTIONS_URL
            create_body = {"version": REPLICATE_LTX_VERSION, "input": model_input}

        create_response = self._session.post(
            create_url,
            headers=headers,
            json=create_body,
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
            context_kwargs: dict[str, Any] = {
                "accept_downloads": True,
                "viewport": {"width": 1440, "height": 900},
                "locale": "en-US",
            }
            if KLING_STORAGE_STATE.exists():
                context_kwargs["storage_state"] = str(KLING_STORAGE_STATE)

            context = await browser.new_context(**context_kwargs)
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
                await self._kling_dismiss_chat_widget(page)
                if debug:
                    await _kling_debug_screenshot(page, "02_after_dismiss")

                if await self._kling_needs_login(page):
                    await self._kling_web_login(page, email, password, debug=debug)
                    if KLING_STORAGE_STATE.parent:
                        KLING_STORAGE_STATE.parent.mkdir(parents=True, exist_ok=True)
                    await context.storage_state(path=str(KLING_STORAGE_STATE))
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
            if await self._kling_login_overlay_visible(page):
                break
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
            if not closed and not await self._kling_login_overlay_visible(page):
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

    async def _kling_dismiss_chat_widget(self, page: Any) -> None:
        """Fecha widget de chat — sem Escape (fecha o modal de login)."""
        if await self._kling_login_overlay_visible(page):
            return
        for selector in KLING_CHAT_DISMISS_SELECTORS:
            locator = page.locator(selector)
            if await locator.count() and await locator.first.is_visible():
                try:
                    await locator.first.click(timeout=2000, force=True)
                    await page.wait_for_timeout(500)
                except Exception:
                    continue

    @staticmethod
    async def _kling_login_overlay_visible(page: Any) -> bool:
        """True se modal/tela de login estiver aberta."""
        welcome = page.get_by_text("Welcome to Kling AI")
        if await welcome.count() and await welcome.first.is_visible():
            return True

        email_buttons = page.locator("div.sign-in-button")
        count = await email_buttons.count()
        for index in range(count):
            button = email_buttons.nth(index)
            if not await button.is_visible():
                continue
            text = (await button.inner_text()).strip().lower()
            if any(token in text for token in ("email", "google", "apple")):
                return True

        email_input = page.locator('input[type="email"]')
        return bool(await email_input.count() and await email_input.first.is_visible())

    async def _kling_surface_login_modal(self, page: Any) -> None:
        """Abre modal de login via One-click Sign In ou botão Generate."""
        if await self._kling_login_overlay_visible(page):
            return

        triggers = (
            'button:has-text("One-click Sign In")',
            'button:has-text("Generate")',
        )
        for selector in triggers:
            locator = page.locator(selector)
            if not await locator.count() or not await locator.first.is_visible():
                continue
            try:
                await locator.first.click(timeout=KLING_SELECTOR_TIMEOUT, force=True)
                await page.wait_for_timeout(1500)
            except Exception:
                continue
            if await self._kling_login_overlay_visible(page):
                return

    async def _kling_wait_for_login_modal(self, page: Any, *, timeout_s: float = 25) -> bool:
        """Aguarda botões de login ou campo e-mail ficarem disponíveis."""
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if await self._kling_login_overlay_visible(page):
                return True
            await self._kling_surface_login_modal(page)
            await page.wait_for_timeout(1000)
        return await self._kling_login_overlay_visible(page)

    async def _kling_click_sign_in_with_email(self, page: Any) -> bool:
        """Clica em Sign in with email (ou variantes) com fallbacks."""
        if await page.locator('input[type="email"]').count():
            if await page.locator('input[type="email"]').first.is_visible():
                return True

        email_buttons = page.locator("div.sign-in-button")
        count = await email_buttons.count()
        for index in range(count):
            button = email_buttons.nth(index)
            if not await button.is_visible():
                continue
            text = (await button.inner_text()).strip().lower()
            if "email" not in text:
                continue
            await button.click(timeout=KLING_SELECTOR_TIMEOUT, force=True)
            return True

        for selector in KLING_EMAIL_ENTRY_SELECTORS:
            locator = page.locator(selector)
            if await locator.count() and await locator.first.is_visible():
                text = (await locator.first.inner_text()).strip().lower()
                if "email" in text or selector.endswith("sign-in-button"):
                    await locator.first.click(timeout=KLING_SELECTOR_TIMEOUT, force=True)
                    return True

        regex_entry = page.get_by_text(
            re.compile(r"(sign in|continue)\s+with\s+email", re.I)
        )
        if await regex_entry.count() and await regex_entry.first.is_visible():
            await regex_entry.first.click(timeout=KLING_SELECTOR_TIMEOUT, force=True)
            return True

        return bool(
            await page.evaluate(
                """() => {
                    const candidates = [
                        ...document.querySelectorAll('.sign-in-button'),
                        ...document.querySelectorAll('button, div, a'),
                    ];
                    const btn = candidates.find((el) =>
                        /sign in with email|continue with email/i.test(
                            (el.textContent || '').trim()
                        )
                    );
                    if (!btn) return false;
                    btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                    btn.click();
                    return true;
                }"""
            )
        )

    @staticmethod
    async def _kling_is_logged_in(page: Any) -> bool:
        """True quando modal de login fechou e botão One-click Sign In sumiu."""
        if await VideoGenerator._kling_login_overlay_visible(page):
            return False

        sign_in = page.locator('button:has-text("One-click Sign In")')
        return not (await sign_in.count() and await sign_in.first.is_visible())

    async def _kling_open_email_login(self, page: Any, *, debug: bool = False) -> None:
        """Abre fluxo e-mail: login modal → Sign in with email → formulário."""
        email_input = page.locator('input[type="email"]')
        if await email_input.count() and await email_input.first.is_visible():
            return

        await self._kling_dismiss_cookies(page)
        await self._kling_dismiss_chat_widget(page)
        await self._kling_surface_login_modal(page)

        if not await self._kling_wait_for_login_modal(page):
            if debug:
                await _kling_debug_screenshot(page, "login_modal_missing")
            raise ElementNotFoundError(
                "Modal de login Kling não abriu — tente KLING_HEADFUL=1 para login manual"
            )

        if debug:
            await _kling_debug_screenshot(page, "login_modal")

        if not await self._kling_click_sign_in_with_email(page):
            if debug:
                await _kling_debug_screenshot(page, "email_button_missing")
            raise ElementNotFoundError(
                'Botão "Sign in with email" não encontrado — UI Kling pode ter mudado'
            )

        await page.wait_for_timeout(2000)
        if debug:
            await _kling_debug_screenshot(page, "email_form")

    @staticmethod
    async def _kling_needs_login(page: Any) -> bool:
        """True se login ainda for necessário."""
        return not await VideoGenerator._kling_is_logged_in(page)

    async def _kling_web_login(
        self,
        page: Any,
        email: str,
        password: str,
        *,
        debug: bool = False,
    ) -> None:
        """Login via One-click Sign In → Sign in with email → Sign In."""
        if await self._page_has_captcha(page):
            raise CaptchaError("CAPTCHA detectado no login Kling")

        await self._kling_open_email_login(page, debug=debug)

        try:
            email_field = await self._kling_find_visible(page, KLING_EMAIL_SELECTORS)
        except ElementNotFoundError as error:
            verification = page.locator(
                'input[placeholder*="verification" i], input[placeholder*="code" i]'
            )
            if await verification.count() and await verification.first.is_visible():
                raise RuntimeError(
                    "Kling exige código de verificação por e-mail (sem campo de senha). "
                    "Use KLING_HEADFUL=1 para concluir login manual uma vez, ou cadastre "
                    "conta com senha em kling.ai."
                ) from error
            raise

        await email_field.fill(email, timeout=KLING_SELECTOR_TIMEOUT)

        password_field = page.locator('input[type="password"]')
        if not (await password_field.count() and await password_field.first.is_visible()):
            raise RuntimeError(
                "Kling não exibiu campo de senha — login por código de e-mail. "
                "Rode com KLING_HEADFUL=1 e salve a sessão em cache/kling_storage_state.json."
            )

        await password_field.first.fill(password, timeout=KLING_SELECTOR_TIMEOUT)
        if debug:
            await _kling_debug_screenshot(page, "password_filled")

        sign_in_btn = page.locator(
            'button:has-text("Sign In"):not([disabled]), '
            'button:has-text("Sign in"):not([disabled]), '
            'button:has-text("Sign In"), '
            'button:has-text("Sign in"), '
            '.generic-button:has-text("Sign In"), '
            '.generic-button:has-text("Sign in")'
        )
        if await sign_in_btn.count():
            await sign_in_btn.first.click(timeout=KLING_SELECTOR_TIMEOUT, force=True)
        else:
            await page.keyboard.press("Enter")

        deadline = time.time() + max(30, KLING_SELECTOR_TIMEOUT // 1000)
        while time.time() < deadline:
            if await self._kling_is_logged_in(page):
                logger.info("Kling: login concluído")
                return

            error_text = page.locator(
                '.el-form-item__error, [class*="error"], [role="alert"]'
            )
            if await error_text.count() and await error_text.first.is_visible():
                message = (await error_text.first.inner_text()).strip()
                if message:
                    raise RuntimeError(
                        f"Login Kling rejeitado: {message}. Verifique KLING_EMAIL/KLING_PASSWORD."
                    )

            await page.wait_for_timeout(1000)

        raise RuntimeError(
            "Login Kling falhou — modal de autenticação ainda visível. "
            "Verifique KLING_EMAIL/KLING_PASSWORD ou rode com KLING_HEADFUL=1 "
            "para login manual (sessão salva em cache/kling_storage_state.json)."
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


def fal_kling_is_configured() -> bool:
    """True se FAL_KEY está presente para Kling 2.6 Pro."""
    return bool(_fal_api_key())


def _fal_api_key() -> str:
    return os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY") or ""


def ai_video_configured() -> bool:
    """True se alguma API de vídeo IA está configurada."""
    return (
        kling_web_is_configured()
        or fal_kling_is_configured()
        or replicate_is_configured()
        or falai_is_configured()
    )


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
        f"| Kling Web (grátis) | {'✅' if kling_web_is_configured() else '❌'} |",
        f"| fal.ai Kling 2.6 Pro | {'✅' if fal_kling_is_configured() else '❌'} |",
        f"| Replicate Wan 2.6 | {'✅' if replicate_is_configured() else '❌'} |",
        f"| fal.ai Wan (HF Router) | {'✅' if falai_is_configured() else '❌'} |",
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
        "1. Kling Web (66 créditos/dia) → fal.ai Kling 2.6 Pro → Replicate Wan 2.6 → HF Wan2.2.",
        "2. Configure FAL_KEY (fal.ai), REPLICATE_API_TOKEN e KLING_EMAIL/PASSWORD.",
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
