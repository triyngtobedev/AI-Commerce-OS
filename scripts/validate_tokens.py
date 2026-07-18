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


def main() -> int:
    global env
    env = dotenv_values(ENV)

    print("Validacao de tokens (.env)\n")
    if not ENV.exists():
        print(f"Arquivo ausente: {ENV}")
        return 1

    replicate = (env.get("REPLICATE_API_TOKEN") or "").strip()
    hf = (env.get("HF_API_TOKEN") or "").strip()
    gemini = (env.get("GEMINI_API_KEY") or "").strip()
    groq = (env.get("GROQ_API_KEY") or "").strip()

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
    ]

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

    print()
    if failed:
        hf = (env.get("HF_API_TOKEN") or "").strip()
        if hf and len(hf) < 20:
            print("Dica: HF_API_TOKEN parece placeholder (ex.: hf_...) — gere em https://huggingface.co/settings/tokens")
        if not (env.get("GEMINI_API_KEY") or "").strip() and not (env.get("GROQ_API_KEY") or "").strip():
            print("Dica: configure GEMINI_API_KEY (Google AI Studio) ou GROQ_API_KEY (console.groq.com) para roteiro.")
        print(f"Resultado: {failed} token(s) com problema.")
        return 1

    print("Resultado: todos os tokens validos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
