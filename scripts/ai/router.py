import os
import time

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
    "llama-3.1-8b-instant",      # substituto do llama3-8b (maior contexto)
    "gemma2-9b-it",              # terceiro fallback
]

GEMINI_MODEL_PRIMARY = "gemini-2.0-flash"
GEMINI_MODEL_LITE = "gemini-2.0-flash-lite"

PRIMARY_GEMINI_CONTEXTS = {"script_generation"}

# Ordem padrão: OpenRouter antes do Groq enquanto cotas free esgotam rápido.
# Amanhã, volte para gemini,groq,openrouter via AI_PROVIDER_ORDER no Railway.
DEFAULT_PROVIDER_ORDER = "gemini,openrouter,groq"

_gemini_daily_quota_exhausted = False


def _provider_order() -> list[str]:
    raw = os.getenv("AI_PROVIDER_ORDER", DEFAULT_PROVIDER_ORDER)
    order = [part.strip().lower() for part in raw.split(",") if part.strip()]
    return order or DEFAULT_PROVIDER_ORDER.split(",")


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
    """Quota diária zerada — pula Gemini nas próximas chamadas, sem esperar 60s."""
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


def _groq_complete(prompt: str, model: str) -> str:
    completion = groq_client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        model=model,
    )

    content = completion.choices[0].message.content
    print(f"[Groq/{model}] response body: {(content or '')[:500]}")

    if not content or not content.strip():
        raise Exception("Groq retornou resposta vazia")

    return content


def _try_groq(prompt: str) -> str:
    last_error: Exception | None = None

    for model in GROQ_MODELS_FALLBACK:
        print(f"[AI Router] Tentando: groq/{model}")
        try:
            return _groq_complete(prompt, model)
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

    raise last_error or Exception("Groq indisponível")


def _openrouter_complete(prompt: str) -> str:
    if not os.getenv("OPENROUTER_API_KEY", "").strip():
        raise Exception("OPENROUTER_API_KEY não configurada")

    print("[OpenRouter] Tentando fallback OpenRouter...")
    return openrouter_generate(prompt)


def _try_openrouter(prompt: str) -> str:
    print("[AI Router] Tentando: openrouter")
    print("⚠️ Provedor anterior indisponível, tentando OpenRouter...")
    return _openrouter_complete(prompt)


def _try_gemini(prompt: str, context_type: str) -> str:
    global _gemini_daily_quota_exhausted
    gemini_model = _gemini_model_for(context_type)

    if _gemini_daily_quota_exhausted:
        print("[AI Router] Gemini quota esgotada — pulando Gemini")
        raise Exception("Gemini quota diária esgotada")

    print("[AI Router] Tentando: gemini")
    try:
        return gemini_generate(prompt, model=gemini_model)
    except Exception as gemini_error:
        print(
            f"⚠️ Gemini indisponível ({gemini_model}, {gemini_error}), "
            "tentando próximo provider..."
        )
        if _is_daily_quota_exhausted(gemini_error):
            print("[Gemini] Quota diária zerada — pulando Gemini nas próximas chamadas")
            _gemini_daily_quota_exhausted = True
        elif _is_rate_limit_error(gemini_error):
            print("[Gemini] Quota/rate limit detectado — aguardando 60s...")
            time.sleep(60)
        raise gemini_error


_PROVIDER_HANDLERS = {
    "gemini": lambda prompt, context_type: _try_gemini(prompt, context_type),
    "openrouter": lambda prompt, _context_type: _try_openrouter(prompt),
    "groq": lambda prompt, _context_type: _try_groq(prompt),
}


def ask_ai(prompt, context_type):
    order = _provider_order()
    print(f"[AI Router] Ordem de fallback: {' → '.join(order)}")
    last_error: Exception | None = None

    for provider in order:
        handler = _PROVIDER_HANDLERS.get(provider)
        if handler is None:
            print(f"[AI Router] Provider desconhecido ignorado: {provider}")
            continue

        try:
            return handler(prompt, context_type)
        except Exception as error:
            last_error = error
            if provider == "openrouter":
                print(f"[OpenRouter] {error}")
            elif provider == "groq":
                print("⚠️ Groq indisponível, tentando próximo provider...")

    print(f"❌ Falha total: {last_error}")
    raise Exception(
        "Nenhuma API de IA disponível."
    ) from last_error
