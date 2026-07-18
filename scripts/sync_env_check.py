"""
Verifica se as variáveis compartilhadas entre .env e infra/.env.n8n
estão em sincronia. Rode antes de qualquer deploy.

Uso: python scripts/sync_env_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import dotenv_values

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ENV = PROJECT_ROOT / ".env"
N8N_ENV = PROJECT_ROOT / "infra" / ".env.n8n"

# Variáveis que devem existir e ter o mesmo valor nos dois arquivos
SHARED_IDENTICAL_VARS = [
    "N8N_WEBHOOK_SECRET",
]

# Variáveis obrigatórias em cada arquivo (podem existir só em um lado)
PYTHON_REQUIRED_VARS = [
    "PIPELINE_API_KEY",
    "PIPELINE_API_BASE_URL",
    "N8N_SCENE_WEBHOOK_URL",
]

N8N_REQUIRED_VARS = [
    "N8N_HOST",
    "WEBHOOK_URL",
]

# Pares equivalentes: (chave .env Python, chave infra/.env.n8n)
SHARED_EQUIVALENT_VARS = [
    ("N8N_SCENE_WEBHOOK_URL", "WEBHOOK_URL"),
]


def _load_env(path: Path) -> dict[str, str | None]:
    if not path.exists():
        return {}
    return dotenv_values(path)


def _normalize(value: str | None) -> str:
    return (value or "").strip()


def _webhook_url_consistent(python_url: str, n8n_base: str) -> bool:
    """N8N_SCENE_WEBHOOK_URL deve estar sob o WEBHOOK_URL público do n8n."""
    if not python_url or not n8n_base:
        return False
    return python_url.startswith(n8n_base.rstrip("/"))


def main() -> int:
    python_values = _load_env(PYTHON_ENV)
    n8n_values = _load_env(N8N_ENV)

    print("Verificação de sincronia .env ↔ infra/.env.n8n\n")
    print(f"  Python: {PYTHON_ENV}")
    print(f"  n8n:    {N8N_ENV}\n")

    has_issues = False

    if not PYTHON_ENV.exists():
        print(f"❌ ausente — {PYTHON_ENV}")
        has_issues = True
    if not N8N_ENV.exists():
        print(f"❌ ausente — {N8N_ENV}")
        has_issues = True

    for var in PYTHON_REQUIRED_VARS:
        value = _normalize(python_values.get(var))
        if value:
            print(f"✅ {var} presente em .env")
        else:
            print(f"❌ {var} ausente ou vazio em .env")
            has_issues = True

    for var in N8N_REQUIRED_VARS:
        value = _normalize(n8n_values.get(var))
        if value:
            print(f"✅ {var} presente em infra/.env.n8n")
        else:
            print(f"❌ {var} ausente ou vazio em infra/.env.n8n")
            has_issues = True

    for var in SHARED_IDENTICAL_VARS:
        py_val = _normalize(python_values.get(var))
        n8n_val = _normalize(n8n_values.get(var))
        if not py_val and not n8n_val:
            print(f"⚠️ {var} ausente nos dois arquivos (opcional, mas recomendado)")
        elif py_val == n8n_val:
            print(f"✅ {var} em sincronia")
        else:
            print(f"⚠️ {var} divergente (.env ≠ infra/.env.n8n)")
            has_issues = True

    for py_key, n8n_key in SHARED_EQUIVALENT_VARS:
        py_val = _normalize(python_values.get(py_key))
        n8n_val = _normalize(n8n_values.get(n8n_key))
        if not py_val:
            print(f"❌ {py_key} ausente em .env")
            has_issues = True
        elif not n8n_val:
            print(f"❌ {n8n_key} ausente em infra/.env.n8n")
            has_issues = True
        elif _webhook_url_consistent(py_val, n8n_val):
            print(f"✅ {py_key} ↔ {n8n_key} em sincronia (prefixo consistente)")
        else:
            print(
                f"⚠️ {py_key} divergente de {n8n_key} "
                f"(esperado que {py_key} comece com {n8n_val.rstrip('/')})"
            )
            has_issues = True

    print()
    if has_issues:
        print("Resultado: falha — corrija divergências antes do deploy.")
        return 1

    print("Resultado: ✅ todos os checks passaram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
