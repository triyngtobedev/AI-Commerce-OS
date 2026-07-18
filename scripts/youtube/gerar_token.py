#!/usr/bin/env python3
"""
Gera YOUTUBE_REFRESH_TOKEN a partir do JSON OAuth do Google Cloud Console.

Uso:
    python scripts/youtube/gerar_token.py

Salva as credenciais em .env.youtube (não altera o .env principal).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_YOUTUBE = PROJECT_ROOT / ".env.youtube"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.publisher.youtube_auth import YOUTUBE_SCOPES


def normalize_path(raw: str) -> Path:
    """Normaliza caminho informado pelo usuário (Windows/Linux)."""
    cleaned = raw.strip().strip('"').strip("'")
    return Path(cleaned).expanduser().resolve()


def extract_oauth_credentials(json_path: Path) -> tuple[str, str]:
    """Valida o JSON OAuth e retorna client_id e client_secret."""
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON inválido: {error}") from error

    if "installed" not in data:
        if "web" in data:
            raise ValueError(
                "Este JSON é do tipo 'Aplicativo Web'. "
                "Crie credenciais do tipo 'Aplicativo para computador' "
                "no Google Cloud Console."
            )
        raise ValueError(
            "JSON inválido: esperado tipo 'Aplicativo para computador' "
            "(chave 'installed')."
        )

    installed = data["installed"]
    client_id = installed.get("client_id", "").strip()
    client_secret = installed.get("client_secret", "").strip()

    if not client_id or not client_secret:
        raise ValueError("client_id ou client_secret ausente no JSON.")

    return client_id, client_secret


def save_env_youtube(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    env_path: Path = ENV_YOUTUBE,
) -> Path:
    """Persiste credenciais YouTube em .env.youtube."""
    values = {
        "YOUTUBE_CLIENT_ID": client_id.strip(),
        "YOUTUBE_CLIENT_SECRET": client_secret.strip(),
        "YOUTUBE_REFRESH_TOKEN": refresh_token.strip(),
    }

    lines: list[str] = []
    updated_keys: set[str] = set()

    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            matched = False
            for key, value in values.items():
                if re.match(rf"^{re.escape(key)}\s*=", line):
                    lines.append(f"{key}={value}")
                    updated_keys.add(key)
                    matched = True
                    break
            if not matched:
                lines.append(line)

    for key, value in values.items():
        if key not in updated_keys:
            lines.append(f"{key}={value}")

    if not lines or not any(line.startswith("#") for line in lines[:3]):
        lines = [
            "# Credenciais YouTube (geradas via scripts/youtube/gerar_token.py)",
            "",
            *lines,
        ]

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return env_path


def run_oauth_flow(json_path: Path):
    """Executa fluxo OAuth interativo e retorna credenciais autorizadas."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as error:
        raise ImportError(
            "google-auth-oauthlib não instalado. "
            "Execute: pip install google-auth-oauthlib google-api-python-client"
        ) from error

    flow = InstalledAppFlow.from_client_secrets_file(
        str(json_path),
        scopes=YOUTUBE_SCOPES,
    )

    server_kwargs: dict = {
        "port": 0,
        "prompt": "consent",
        "access_type": "offline",
        "authorization_prompt_message": "\nAbra essa URL no navegador:\n{url}\n",
    }

    if sys.platform == "win32":
        server_kwargs["browser"] = "windows-default"

    return flow.run_local_server(**server_kwargs)


def main() -> int:
    print("\n=== Gerar YouTube Refresh Token ===\n")
    print(
        "Informe o caminho do arquivo JSON baixado do Google Cloud Console.\n"
        "Exemplo Windows: C:\\Users\\SeuNome\\Downloads\\client_secret_....json\n"
    )

    raw_path = input("Caminho do JSON: ")
    if not raw_path.strip():
        print("\n❌ Caminho não informado.")
        return 1

    json_path = normalize_path(raw_path)
    if not json_path.exists():
        print(f"\n❌ Arquivo não encontrado: {json_path}")
        return 1

    try:
        client_id, client_secret = extract_oauth_credentials(json_path)
    except ValueError as error:
        print(f"\n❌ {error}")
        return 1

    print("\n🌐 Abrindo navegador para autorização...")
    print("Faça login com a conta do canal YouTube e conceda as permissões.\n")

    try:
        credentials = run_oauth_flow(json_path)
    except ImportError as error:
        print(f"\n❌ {error}")
        return 1
    except Exception as error:
        print(f"\n❌ Falha na autorização OAuth: {error}")
        return 1

    refresh_token = credentials.refresh_token
    if not refresh_token:
        print("\n❌ Refresh token não retornado pelo Google.")
        print("   Revogue o acesso em https://myaccount.google.com/permissions")
        print("   e execute o script novamente.")
        return 1

    print("\n=== Copie estes valores para Railway → Variables ===\n")
    print(f"YOUTUBE_CLIENT_ID={client_id}")
    print(f"YOUTUBE_CLIENT_SECRET={client_secret}")
    print(f"YOUTUBE_REFRESH_TOKEN={refresh_token}")

    env_file = save_env_youtube(client_id, client_secret, refresh_token)
    print(f"\n✅ Valores salvos em: {env_file.resolve()}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
