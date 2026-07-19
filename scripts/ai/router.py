import os
import time

from dotenv import load_dotenv
from groq import Groq

from scripts.ai.providers.gemini import generate as gemini_generate
from scripts.ai.providers.openrouter import generate as openrouter_generate

load_dotenv()

_groq_client = None


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise Exception("GROQ_API_KEY não configurada")
        _groq_client = Groq(api_key=api_key)
    return _groq_client

GROQ_MODELS_FALLBACK = [
    "llama-3.3-70b-versatile",   # primário (12k TPM)
    "llama-3.1-8b-instant",      # substituto do llama3-8b (maior contexto)
    "gemma2-9b-it",              # terceiro fallback
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
    completion = _get_groq_client().chat.completions.create(
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


def _has_key(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


class AIRouter:
    """Facade do router — expõe health check para preflight do batch Sprint 30."""

    def health(self) -> dict:
        from pathlib import Path

        from scripts.core.feature_flags import sprint30_flags_snapshot

        ai = {
            "gemini": _has_key("GEMINI_API_KEY"),
            "groq": _has_key("GROQ_API_KEY"),
            "openrouter": _has_key("OPENROUTER_API_KEY"),
        }
        footage = {
            "pexels": _has_key("PEXELS_API_KEY"),
            "pixabay": _has_key("PIXABAY_API_KEY"),
        }
        tts = {
            "azure": _has_key("AZURE_SPEECH_KEY") and _has_key("AZURE_SPEECH_REGION"),
            "edge_fallback": True,
            "gtts_fallback": True,
        }

        missing: list[str] = []
        if not any(ai.values()):
            missing.append("IA: defina GEMINI_API_KEY, GROQ_API_KEY ou OPENROUTER_API_KEY")
        if not footage["pexels"]:
            missing.append("Footage: defina PEXELS_API_KEY")
        if not tts["azure"]:
            missing.append(
                "TTS: defina AZURE_SPEECH_KEY + AZURE_SPEECH_REGION "
                "(ou aceite fallback Edge/gTTS gratuito)"
            )

        audio_library = Path("assets/audio/library.json").exists()
        has_tts = tts["azure"] or tts["edge_fallback"]

        return {
            "ready_for_batch": any(ai.values()) and footage["pexels"] and has_tts,
            "ready_for_batch_strict": len(missing) == 0,
            "ai": ai,
            "ai_any": any(ai.values()),
            "footage": footage,
            "tts": tts,
            "audio_library": audio_library,
            "sprint30_flags": sprint30_flags_snapshot(),
            "missing_required": missing,
            "hint": "cp .env.sprint30.example .env e preencha as chaves",
        }


def get_client() -> AIRouter:
    return AIRouter()
