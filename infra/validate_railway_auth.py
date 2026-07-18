#!/usr/bin/env python3
"""
Valida autenticação n8n → Railway.

Verifica se a chave local bate com o Railway e se o header X-API-Key funciona.

Uso:
    python infra/validate_railway_auth.py
    python infra/validate_railway_auth.py --url https://seu-app.up.railway.app --key SUA_CHAVE
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_MAIN = ROOT / ".env"
ENV_N8N = ROOT / "infra" / ".env.n8n"


def load_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip()
    return data


def resolve_api_key(env_main: dict[str, str]) -> str:
    cloud = env_main.get("CLOUD_API_KEY", "").strip()
    pipeline = env_main.get("PIPELINE_API_KEY", "").strip()
    return cloud or pipeline


def resolve_api_url(env_main: dict[str, str], env_n8n: dict[str, str]) -> str:
    for source in (env_main, env_n8n):
        for key in ("CLOUD_API_URL", "PIPELINE_API_BASE_URL"):
            value = source.get(key, "").strip()
            if value:
                return value.rstrip("/")
    return "https://ai-commerce-os-production-b4f9.up.railway.app"


def check_health(base_url: str) -> dict:
    url = f"{base_url}/api/v1/health"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def check_pipeline_run(base_url: str, api_key: str) -> tuple[int, dict | str]:
    url = f"{base_url}/api/v1/pipeline/run"
    payload = json.dumps({"platform": "youtube_dark", "topic": "teste auth validate"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = raw
        return exc.code, body


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida auth n8n → Railway")
    parser.add_argument("--url", default="", help="URL base do Railway")
    parser.add_argument("--key", default="", help="PIPELINE_API_KEY")
    args = parser.parse_args()

    env_main = load_env(ENV_MAIN)
    env_n8n = load_env(ENV_N8N)

    api_key = args.key.strip() or resolve_api_key(env_main) or env_n8n.get("PIPELINE_API_KEY", "").strip()
    base_url = args.url.strip() or resolve_api_url(env_main, env_n8n)

    print(f"URL:  {base_url}")
    print(f"Key:  {'***' + api_key[-4:] if len(api_key) >= 4 else '(vazia)'}")

    # Verifica consistência local
    main_key = resolve_api_key(env_main)
    n8n_key = env_n8n.get("PIPELINE_API_KEY", "").strip()
    if main_key and n8n_key and main_key != n8n_key:
        print("\n⚠️  AVISO: .env e infra/.env.n8n têm chaves DIFERENTES")
        print(f"   .env PIPELINE/CLOUD: ***{main_key[-4:]}")
        print(f"   .env.n8n:            ***{n8n_key[-4:]}")

    if not api_key:
        print("\n❌ ERRO: Nenhuma chave encontrada.")
        print("   1. Copie PIPELINE_API_KEY do Railway → Variables")
        print("   2. Cole em .env (CLOUD_API_KEY e PIPELINE_API_KEY)")
        print("   3. Rode infra/ativar-n8n.ps1 para sincronizar infra/.env.n8n")
        return 1

    print("\n--- Health check ---")
    try:
        health = check_health(base_url)
        print(f"Status: {health.get('status')}")
        print(f"Auth configured: {health.get('auth_configured')}")
        if not health.get("auth_configured"):
            print("❌ Railway sem PIPELINE_API_KEY configurada (retornaria 503)")
            return 1
    except Exception as exc:
        print(f"❌ Health check falhou: {exc}")
        return 1

    print("\n--- POST /pipeline/run (com X-API-Key) ---")
    status, body = check_pipeline_run(base_url, api_key)

    if status == 202:
        print(f"✅ OK — HTTP 202")
        print(f"   job_id: {body.get('job_id') if isinstance(body, dict) else body}")
        print("\nAutenticação n8n → Railway está correta.")
        return 0

    if status == 401:
        print(f"❌ ERRO 401 — chave NÃO bate com o Railway")
        print(f"   Resposta: {body}")
        print("\nCorreção:")
        print("   1. railway.app → seu projeto → Variables → copie PIPELINE_API_KEY")
        print("   2. Cole no .env: CLOUD_API_KEY=<valor> e PIPELINE_API_KEY=<valor>")
        print("   3. Rode: .\\infra\\ativar-n8n.ps1")
        print("   4. Rode: python infra/setup_n8n.py  (sincroniza credencial n8n)")
        return 1

    print(f"⚠️  HTTP {status}: {body}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
