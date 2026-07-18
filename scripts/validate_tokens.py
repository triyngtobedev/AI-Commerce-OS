#!/usr/bin/env python3
"""Valida tokens de API sem expor valores completos."""

from __future__ import annotations

import sys
from pathlib import Path

import requests
from dotenv import dotenv_values

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"

env: dict[str, str | None] = {}


def mask(value: str | None) -> str:
    value = (value or "").strip()
    if not value:
        return "(vazio)"
    if len(value) <= 8:
        return value[:2] + "***"
    return f"{value[:4]}...{value[-4:]}"


def check_http(
    name: str,
    url: str,
    headers: dict[str, str] | None = None,
    *,
    ok_statuses: tuple[int, ...] = (200,),
) -> dict:
    token = (env.get(name) or "").strip()
    if not token:
        return {"name": name, "set": False, "ok": False, "status": None, "detail": "nao configurado"}

    hdrs = {
        "User-Agent": "AI-Commerce-OS/1.0 (+https://github.com/local/ai-commerce-os)",
        "Accept": "application/json",
    }
    hdrs.update(headers or {})
    try:
        resp = requests.get(url, headers=hdrs, timeout=25)
        ok = resp.status_code in ok_statuses
        detail = "OK" if ok else resp.text[:240]
        return {
            "name": name,
            "set": True,
            "ok": ok,
            "status": resp.status_code,
            "detail": detail,
            "masked": mask(token),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "name": name,
            "set": True,
            "ok": False,
            "status": None,
            "detail": str(exc),
            "masked": mask(token),
        }


def check_openrouter(api_key: str) -> dict:
    if not api_key:
        return {
            "name": "OPENROUTER_API_KEY",
            "set": False,
            "ok": False,
            "status": None,
            "detail": "nao configurado (openrouter.ai/keys)",
            "masked": mask(api_key),
        }

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/triyngtobedev/AI-Commerce-OS",
                "X-OpenRouter-Title": "Vibecoder AI-Commerce-OS",
            },
            json={
                "model": "mistralai/mistral-7b-instruct:free",
                "messages": [{"role": "user", "content": "Responda apenas: OK"}],
            },
            timeout=45,
        )
        ok = resp.status_code == 200 and "OK" in resp.text.upper()
        return {
            "name": "OPENROUTER_API_KEY",
            "set": True,
            "ok": ok,
            "status": resp.status_code,
            "detail": "OK" if ok else resp.text[:240],
            "masked": mask(api_key),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "name": "OPENROUTER_API_KEY",
            "set": True,
            "ok": False,
            "status": None,
            "detail": str(exc),
            "masked": mask(api_key),
        }


def main() -> int:
    global env
    env = dotenv_values(ENV)

    print("Validacao de tokens (.env)\n")
    if not ENV.exists():
        print(f"Arquivo ausente: {ENV}")
        return 1

    replicate = (env.get("REPLICATE_API_TOKEN") or "").strip()
    hf = (env.get("HF_API_TOKEN") or "").strip()
    fal_key = (env.get("FAL_KEY") or env.get("FAL_API_KEY") or "").strip()
    gemini = (env.get("GEMINI_API_KEY") or "").strip()
    groq = (env.get("GROQ_API_KEY") or "").strip()
    openrouter = (env.get("OPENROUTER_API_KEY") or "").strip()
    pexels = (env.get("PEXELS_API_KEY") or "").strip()
    kling_email = (env.get("KLING_EMAIL") or "").strip()
    kling_password = (env.get("KLING_PASSWORD") or "").strip()

    checks = [
        check_http(
            "REPLICATE_API_TOKEN",
            "https://api.replicate.com/v1/account",
            {"Authorization": f"Bearer {replicate}"},
        ),
        check_http(
            "HF_API_TOKEN",
            "https://huggingface.co/api/whoami-v2",
            {"Authorization": f"Bearer {hf}"},
        ),
        check_http(
            "GEMINI_API_KEY",
            f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini}",
        ),
        check_http(
            "GROQ_API_KEY",
            "https://api.groq.com/openai/v1/models",
            {"Authorization": f"Bearer {groq}"},
        ),
        check_openrouter(openrouter),
    ]

    if pexels:
        checks.append(
            check_http(
                "PEXELS_API_KEY",
                "https://api.pexels.com/v1/search?query=test&per_page=1",
                {"Authorization": pexels},
            )
        )
    else:
        checks.append(
            {
                "name": "PEXELS_API_KEY",
                "set": False,
                "ok": False,
                "status": None,
                "detail": "nao configurado (pexels.com/api)",
                "masked": mask(pexels),
            }
        )

    optional = []
    if fal_key:
        optional.append(
            {
                "name": "FAL_KEY",
                "set": True,
                "ok": len(fal_key) >= 20,
                "status": None,
                "detail": "OK" if len(fal_key) >= 20 else "token curto demais",
                "masked": mask(fal_key),
            }
        )
    else:
        optional.append(
            {
                "name": "FAL_KEY",
                "set": False,
                "ok": False,
                "status": None,
                "detail": "nao configurado (fal.ai Kling 2.6 Pro)",
                "masked": mask(fal_key),
            }
        )

    if kling_email and kling_password:
        optional.append(
            {
                "name": "KLING_WEB",
                "set": True,
                "ok": True,
                "status": None,
                "detail": "credenciais presentes (tier grátis Playwright)",
                "masked": mask(kling_email),
            }
        )
    else:
        optional.append(
            {
                "name": "KLING_WEB",
                "set": False,
                "ok": False,
                "status": None,
                "detail": "KLING_EMAIL/PASSWORD ausentes",
                "masked": mask(kling_email),
            }
        )

    failed = 0
    for item in checks:
        status = item.get("status")
        status_txt = status if status is not None else "-"
        icon = "OK" if item["ok"] else "FAIL"
        token_txt = item.get("masked", mask(env.get(item["name"])))
        print(f"[{icon}] {item['name']} token={token_txt} HTTP={status_txt}")
        if not item["ok"]:
            failed += 1
            print(f"      {item['detail']}")

    print("\nVideo IA (opcional):")
    for item in optional:
        status_txt = item.get("status") if item.get("status") is not None else "-"
        icon = "OK" if item["ok"] else "INFO"
        token_txt = item.get("masked", "-")
        print(f"[{icon}] {item['name']} token={token_txt} HTTP={status_txt}")
        if not item["ok"]:
            print(f"      {item['detail']}")

    print()
    if failed:
        hf_token = (env.get("HF_API_TOKEN") or "").strip()
        if hf_token and len(hf_token) < 20:
            print("Dica: HF_API_TOKEN parece placeholder (ex.: hf_...) — gere em https://huggingface.co/settings/tokens")
        if not fal_key:
            print("Dica: FAL_KEY em fal.ai/dashboard/keys — Kling 2.6 Pro (~$0,35/clip 5s)")
        if (
            not (env.get("GEMINI_API_KEY") or "").strip()
            and not (env.get("GROQ_API_KEY") or "").strip()
            and not openrouter
        ):
            print(
                "Dica: configure GEMINI_API_KEY, GROQ_API_KEY ou OPENROUTER_API_KEY para roteiro."
            )
        if not pexels:
            print("Dica: PEXELS_API_KEY em pexels.com/api — obrigatório para footage lofi_dark.")
        print(f"Resultado: {failed} token(s) com problema.")
        return 1

    print("Resultado: todos os tokens validos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
