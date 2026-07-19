import os
import shutil
import time
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from scripts.ai.providers.gemini import generate as gemini_generate
from scripts.ai.providers.openrouter import generate as openrouter_generate

load_dotenv()

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

GROQ_MODELS_FALLBACK = [
    "llama-3.3-70b-versatile",   # primário (12k TPM)
    "openai/gpt-oss-120b",       # contexto grande (~131k) — roteiros longos
    "llama-3.1-8b-instant",      # substituto leve
]

GEMINI_MODEL_PRIMARY = "gemini-2.0-flash"
GEMINI_MODEL_LITE = "gemini-2.0-flash-lite"

PRIMARY_GEMINI_CONTEXTS = {"script_generation"}

GROQ_MAX_TOKENS = {
    "script_generation": 16384,
    "script_rewrite": 8192,
    "script_expansion": 4096,
    "strategy": 4096,
    "analysis": 2048,
    "content_generation": 4096,
}

_gemini_daily_quota_exhausted = False


def _gemini_model_for(context_type: str) -> str:
    if context_type in PRIMARY_GEMINI_CONTEXTS:
        return GEMINI_MODEL_PRIMARY
    return GEMINI_MODEL_LITE


def _is_rate_limit_error(error: Exception) -> bool:
    msg = str(error).lower()
    return any(
        token in msg
        for token in (
            "429",
            "quota",
            "resource_exhausted",
            "rate limit",
            "too many requests",
        )
    )


def _is_daily_quota_exhausted(error: Exception) -> bool:
    """Quota diária zerada — retry imediato no Groq, sem esperar 60s."""
    return "limit: 0" in str(error).lower()


def _is_request_too_large(error: Exception) -> bool:
    msg = str(error).lower()
    return (
        "413" in msg
        or "request too large" in msg
        or "payload too large" in msg
        or ("token" in msg and ("limit" in msg or "exceed" in msg))
    )


def _groq_error_details(error: Exception) -> str:
    status = getattr(error, "status_code", None)
    body = getattr(error, "body", None)
    if body is not None:
        return f"status={status} body={str(body)[:500]}"
    return f"status={status} error={str(error)[:500]}"


def _groq_complete(prompt: str, model: str, context_type: str = "") -> str:
    max_tokens = GROQ_MAX_TOKENS.get(context_type, 4096)
    completion = groq_client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        model=model,
        max_tokens=max_tokens,
    )

    content = completion.choices[0].message.content
    print(f"[Groq/{model}] response body: {(content or '')[:500]}")

    if not content or not content.strip():
        raise Exception("Groq retornou resposta vazia")

    return content


def _openrouter_complete(prompt: str) -> str:
    if not os.getenv("OPENROUTER_API_KEY", "").strip():
        raise Exception("OPENROUTER_API_KEY não configurada")

    print("[OpenRouter] Tentando fallback OpenRouter...")
    return openrouter_generate(prompt)


def ask_ai(prompt, context_type):
    global _gemini_daily_quota_exhausted
    gemini_model = _gemini_model_for(context_type)

    if not _gemini_daily_quota_exhausted:
        print("[AI Router] Tentando: gemini")
        try:
            return gemini_generate(prompt, model=gemini_model)
        except Exception as gemini_error:
            print(
                f"⚠️ Gemini indisponível ({gemini_model}, {gemini_error}), tentando Groq..."
            )
            if _is_daily_quota_exhausted(gemini_error):
                print("[Gemini] Quota diária zerada — pulando Gemini nas próximas chamadas")
                _gemini_daily_quota_exhausted = True
            elif _is_rate_limit_error(gemini_error):
                print("[Gemini] Quota/rate limit detectado — aguardando 60s...")
                time.sleep(60)

            if gemini_model == GEMINI_MODEL_PRIMARY:
                print(f"[AI Router] Tentando: gemini/{GEMINI_MODEL_LITE}")
                try:
                    return gemini_generate(prompt, model=GEMINI_MODEL_LITE)
                except Exception as lite_error:
                    print(f"⚠️ Gemini lite indisponível ({lite_error}), tentando Groq...")
    else:
        print("[AI Router] Gemini quota esgotada — usando Groq direto")

    # 2. Tenta Groq com fallback de modelos
    last_error = None

    for model in GROQ_MODELS_FALLBACK:
        print(f"[AI Router] Tentando: groq/{model}")
        try:
            return _groq_complete(prompt, model, context_type)
        except Exception as error:
            last_error = error
            print(f"[Groq/{model}] {_groq_error_details(error)}")

            if _is_request_too_large(error):
                print(
                    f"[Groq] Prompt grande demais para {model}, "
                    "tentando modelo com contexto maior..."
                )
                continue

            if _is_rate_limit_error(error):
                print(f"[Groq/{model}] Rate limit — tentando próximo modelo...")
                continue

            print(f"[Groq/{model}] Falha — tentando próximo modelo...")

    # 3. Tenta OpenRouter
    print("[AI Router] Tentando: openrouter")
    print("⚠️ Groq indisponível, tentando OpenRouter...")
    try:
        return _openrouter_complete(prompt)
    except Exception as openrouter_error:
        print(f"[OpenRouter] {openrouter_error}")
        print(f"❌ Falha total: {openrouter_error}")
        raise Exception(
            "Nenhuma API de IA disponível."
        ) from (openrouter_error if last_error is None else last_error)


def _env_present(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def _detect_tts_provider() -> str:
    if _env_present("AZURE_SPEECH_KEY") and _env_present("AZURE_SPEECH_REGION"):
        return "azure"
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        pass
    else:
        return "edge"
    return "gtts"


def _ai_provider_status() -> dict[str, Any]:
    providers = {
        "gemini": _env_present("GEMINI_API_KEY"),
        "groq": _env_present("GROQ_API_KEY"),
        "openrouter": _env_present("OPENROUTER_API_KEY"),
    }
    ready = any(providers.values())
    primary = "none"
    if providers["gemini"]:
        primary = "gemini"
    elif providers["groq"]:
        primary = "groq"
    elif providers["openrouter"]:
        primary = "openrouter"

    return {
        "status": "ready" if ready else "missing_keys",
        "primary": primary,
        "providers": providers,
    }


class AIRouterClient:
    """Cliente leve para health checks e batch Sprint 30."""

    def health(self) -> dict[str, Any]:
        from scripts.sprint30.config import get_flags, is_sprint30_enabled

        missing_required: list[str] = []

        ai = _ai_provider_status()
        if ai["status"] != "ready":
            missing_required.append("AI_KEY (GEMINI_API_KEY ou GROQ_API_KEY ou OPENROUTER_API_KEY)")

        has_stock_media = _env_present("PEXELS_API_KEY") or _env_present("PIXABAY_API_KEY")
        if not has_stock_media:
            missing_required.append("PEXELS_API_KEY (ou PIXABAY_API_KEY como fallback)")

        ffmpeg_ok = shutil.which("ffmpeg") is not None
        if not ffmpeg_ok:
            missing_required.append("ffmpeg (PATH)")

        tts_provider = _detect_tts_provider()
        flags = get_flags()
        if not is_sprint30_enabled():
            flags = {
                "SPRINT30": False,
                "FOOTAGE_FIRST": False,
                "RETENTION_CONTROLLER": False,
            }

        return {
            "ready_for_batch": len(missing_required) == 0,
            "missing_required": missing_required,
            "flags": flags,
            "tts": {
                "provider": tts_provider,
                "azure_configured": _env_present("AZURE_SPEECH_KEY")
                and _env_present("AZURE_SPEECH_REGION"),
            },
            "ai": ai,
            "tools": {
                "ffmpeg": ffmpeg_ok,
            },
        }


_client: AIRouterClient | None = None


def get_client() -> AIRouterClient:
    global _client
    if _client is None:
        _client = AIRouterClient()
    return _client
