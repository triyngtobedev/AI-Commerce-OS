import os

from dotenv import load_dotenv
from groq import Groq

from scripts.ai.groq_tracker import groq_call_tracked
from scripts.ai.providers.openrouter import generate as openrouter_generate

load_dotenv()

_groq_client = None

GROQ_MODEL_DEFAULT = "llama-3.1-8b-instant"
GROQ_MODEL_SCRIPT = "llama-3.3-70b-versatile"
OPENROUTER_MODEL = "mistralai/mistral-7b-instruct-v0.3"
OPENROUTER_FALLBACK_MODELS = [
    "mistralai/mistral-7b-instruct-v0.3",
    "groq/gemma2-9b-it",
]

MAX_PROMPT_TOKENS = 3500
_CHARS_PER_TOKEN = 4

SCRIPT_GENERATION_CONTEXTS = {"script_generation"}

GROQ_MAX_TOKENS = {
    "script_generation": 16384,
    "script_rewrite": 8192,
    "script_expansion": 4096,
    "strategy": 4096,
    "analysis": 2048,
    "content_generation": 4096,
}


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise Exception("GROQ_API_KEY não configurada")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


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


def _truncate_prompt(prompt: str, max_tokens: int = MAX_PROMPT_TOKENS) -> str:
    """Trunca prompt que excede limite de tokens (estimativa por caracteres)."""
    max_chars = max_tokens * _CHARS_PER_TOKEN
    if len(prompt) <= max_chars:
        return prompt

    estimated_tokens = len(prompt) // _CHARS_PER_TOKEN
    print(
        f"[AI Router] Prompt truncado de ~{estimated_tokens} para "
        f"{max_tokens} tokens"
    )
    return prompt[:max_chars]


def _groq_models_for(context_type: str) -> list[str]:
    models = [GROQ_MODEL_DEFAULT]
    if context_type in SCRIPT_GENERATION_CONTEXTS:
        models.append(GROQ_MODEL_SCRIPT)
    return models


def _groq_complete(prompt: str, model: str, context_type: str = "") -> str:
    max_tokens = GROQ_MAX_TOKENS.get(context_type, 4096)
    client = _get_groq_client()
    completion = groq_call_tracked(
        client,
        etapa=context_type or "groq_complete",
        messages=[{"role": "user", "content": prompt}],
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

    last_error = None
    for model in OPENROUTER_FALLBACK_MODELS:
        print(f"[OpenRouter] Tentando fallback OpenRouter ({model})...")
        try:
            return openrouter_generate(prompt, model=model)
        except Exception as error:
            last_error = error
            print(f"[OpenRouter/{model}] {error}")

    raise Exception(
        f"OpenRouter indisponível após {len(OPENROUTER_FALLBACK_MODELS)} modelos"
    ) from last_error


def ask_ai(prompt, context_type):
    prompt = _truncate_prompt(prompt)
    last_error = None

    for model in _groq_models_for(context_type):
        print(f"[AI Router] Tentando: groq/{model}")
        try:
            return _groq_complete(prompt, model, context_type)
        except Exception as error:
            last_error = error
            print(f"[Groq/{model}] {_groq_error_details(error)}")

            if _is_request_too_large(error):
                print(
                    f"[Groq] Prompt grande demais para {model}, "
                    "tentando próximo modelo..."
                )
                continue

            if _is_rate_limit_error(error):
                print(f"[Groq/{model}] Rate limit — tentando próximo modelo...")
                continue

            print(f"[Groq/{model}] Falha — tentando próximo modelo...")

    print(f"[AI Router] Tentando: openrouter/{OPENROUTER_MODEL}")
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
            "groq": _has_key("GROQ_API_KEY"),
            "openrouter": _has_key("OPENROUTER_API_KEY"),
            "gemini": _has_key("GEMINI_API_KEY"),
        }
        footage = {
            "youtube_cc": True,
            "wikimedia": True,
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
            missing.append("IA: defina GROQ_API_KEY ou OPENROUTER_API_KEY")
        if not (footage["pexels"] or footage["pixabay"]):
            missing.append(
                "Footage opcional: PEXELS_API_KEY ou PIXABAY_API_KEY "
                "(Wikimedia Commons funciona sem chave)"
            )
        if not tts["azure"]:
            missing.append(
                "TTS: defina AZURE_SPEECH_KEY + AZURE_SPEECH_REGION "
                "(ou aceite fallback Edge/gTTS gratuito)"
            )

        audio_library = Path("assets/audio/library.json").exists()
        has_tts = tts["azure"] or tts["edge_fallback"]

        from scripts.utils.merge_conflict_scan import find_merge_conflicts

        merge_conflicts = find_merge_conflicts(Path(__file__).resolve().parents[2])
        if merge_conflicts:
            first = merge_conflicts[0]
            missing.append(
                f"Merge: resolva conflitos Git em {first['path']}:{first['line']} "
                f"({len(merge_conflicts)} marcador(es))"
            )

        return {
            "ready_for_batch": (
                any(ai.values()) and footage["wikimedia"] and has_tts and not merge_conflicts
            ),
            "ready_for_batch_strict": len(missing) == 0,
            "ai": ai,
            "ai_any": any(ai.values()),
            "footage": footage,
            "tts": tts,
            "audio_library": audio_library,
            "sprint30_flags": sprint30_flags_snapshot(),
            "missing_required": missing,
            "merge_conflicts": merge_conflicts[:5],
            "merge_conflicts_count": len(merge_conflicts),
            "hint": "cp .env.sprint30.example .env e preencha as chaves",
        }


def get_client() -> AIRouter:
    return AIRouter()
