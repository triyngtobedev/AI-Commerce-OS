"""
YouTube OAuth2 — configuração, validação e fluxo interativo.

Variáveis de ambiente:
    YOUTUBE_CLIENT_ID
    YOUTUBE_CLIENT_SECRET
    YOUTUBE_REFRESH_TOKEN
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

ENV_FILE = Path(".env")

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

ENV_KEYS = (
    "YOUTUBE_CLIENT_ID",
    "YOUTUBE_CLIENT_SECRET",
    "YOUTUBE_REFRESH_TOKEN",
)


@dataclass
class CredentialStatus:
    """Resultado da validação de credenciais YouTube."""

    configured: bool
    valid: bool
    missing: List[str] = field(default_factory=list)
    invalid: List[str] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)
    channel_title: Optional[str] = None
    channel_id: Optional[str] = None

    def summary(self) -> str:
        lines = ["=== Configuração YouTube OAuth ==="]

        for message in self.messages:
            lines.append(message)

        if self.channel_title:
            lines.append(f"Canal conectado: {self.channel_title}")

        if not self.configured:
            lines.append("")
            lines.append("Como configurar:")
            lines.append(
                "  1. Crie credenciais OAuth no Google Cloud Console"
            )
            lines.append(
                "  2. Ative YouTube Data API v3 e YouTube Analytics API"
            )
            lines.append(
                "  3. Execute: python main.py --youtube-auth"
            )
            lines.append(
                "  4. Ou preencha manualmente o .env"
            )
            lines.append("")
            lines.append(
                "Documentação: docs/youtube_oauth.md"
            )

        return "\n".join(lines)


def get_env_credentials() -> Dict[str, Optional[str]]:
    """Carrega credenciais do ambiente."""

    return {
        "client_id": os.getenv("YOUTUBE_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("YOUTUBE_CLIENT_SECRET", "").strip(),
        "refresh_token": os.getenv("YOUTUBE_REFRESH_TOKEN", "").strip(),
    }


def _is_placeholder(value: str) -> bool:
    """Detecta valores vazios ou placeholders comuns."""

    value = value.strip()

    if not value:
        return True

    placeholders = {
        "your_client_id",
        "your_client_secret",
        "your_refresh_token",
        "seu_client_id",
        "seu_client_secret",
        "seu_refresh_token",
        "xxx",
        "changeme",
    }

    return value.lower() in placeholders


def validate_credentials(
    test_connection: bool = False,
) -> CredentialStatus:
    """
    Valida presença e formato das credenciais YouTube.

    Args:
        test_connection: Se True, testa conexão com a API
    """

    creds = get_env_credentials()
    missing = []
    invalid = []
    messages = []

    labels = {
        "client_id": "YOUTUBE_CLIENT_ID",
        "client_secret": "YOUTUBE_CLIENT_SECRET",
        "refresh_token": "YOUTUBE_REFRESH_TOKEN",
    }

    for key, label in labels.items():
        value = creds[key]

        if _is_placeholder(value):
            missing.append(label)
            messages.append(f"❌ {label} — ausente ou não configurado")
            continue

        messages.append(f"✅ {label} — presente")

        if key == "client_id" and not value.endswith(
            ".apps.googleusercontent.com"
        ):
            invalid.append(label)
            messages.append(
                f"⚠️ {label} — formato inválido "
                "(esperado: *.apps.googleusercontent.com)"
            )

    configured = not missing
    valid = configured and not invalid
    channel_title = None
    channel_id = None

    if test_connection and configured and not invalid:

        connection = _test_api_connection(creds)

        if connection["ok"]:
            valid = True
            channel_title = connection.get("channel_title")
            channel_id = connection.get("channel_id")
            messages.append("✅ Conexão com YouTube API — OK")
        else:
            valid = False
            messages.append(
                f"❌ Conexão com YouTube API — {connection['error']}"
            )

            if "invalid_grant" in connection["error"].lower():
                messages.append(
                    "   O refresh token expirou ou foi revogado. "
                    "Execute: python main.py --youtube-auth"
                )

    elif test_connection and not configured:
        messages.append(
            "⏭️ Teste de conexão ignorado — credenciais incompletas"
        )

    return CredentialStatus(
        configured=configured,
        valid=valid,
        missing=missing,
        invalid=invalid,
        messages=messages,
        channel_title=channel_title,
        channel_id=channel_id,
    )


def is_upload_configured() -> bool:
    """Verifica se credenciais mínimas estão presentes."""

    return validate_credentials().configured


def build_google_credentials(
    creds: Optional[Dict[str, str]] = None,
):
    """
    Constrói objeto Credentials do google-auth.

    Raises:
        ValueError: Se credenciais ausentes ou inválidas
    """

    if creds is None:
        creds = get_env_credentials()

    status = validate_credentials()

    if not status.configured:
        raise ValueError(
            "Credenciais YouTube incompletas. "
            f"Ausentes: {', '.join(status.missing)}. "
            "Execute: python main.py --youtube-auth"
        )

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError as error:
        raise ImportError(
            "Dependências OAuth não instaladas. "
            "Execute: pip install google-api-python-client "
            "google-auth-oauthlib"
        ) from error

    credentials = Credentials(
        token=None,
        refresh_token=creds["refresh_token"],
        client_id=creds["client_id"],
        client_secret=creds["client_secret"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=YOUTUBE_SCOPES,
    )

    try:
        credentials.refresh(Request())
    except Exception as error:
        error_msg = str(error)

        if "invalid_grant" in error_msg.lower():
            raise ValueError(
                "Refresh token inválido ou expirado. "
                "Execute: python main.py --youtube-auth"
            ) from error

        raise ValueError(
            f"Falha ao renovar token de acesso: {error_msg}"
        ) from error

    return credentials


def _test_api_connection(
    creds: Dict[str, str],
) -> Dict[str, Any]:
    """Testa conexão listando canal do usuário autenticado."""

    try:
        from googleapiclient.discovery import build

        credentials = build_google_credentials(creds)

        youtube = build(
            "youtube",
            "v3",
            credentials=credentials,
        )

        response = youtube.channels().list(
            part="snippet",
            mine=True,
        ).execute()

        items = response.get("items", [])

        if not items:
            return {
                "ok": False,
                "error": "Nenhum canal encontrado para esta conta",
            }

        channel = items[0]

        return {
            "ok": True,
            "channel_id": channel["id"],
            "channel_title": channel["snippet"]["title"],
        }

    except ValueError as error:
        return {"ok": False, "error": str(error)}

    except Exception as error:
        return {"ok": False, "error": str(error)}


def save_credentials_to_env(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    env_path: Path = ENV_FILE,
) -> Path:
    """
    Persiste credenciais no arquivo .env.

    Atualiza variáveis existentes ou cria o arquivo.
    """

    values = {
        "YOUTUBE_CLIENT_ID": client_id.strip(),
        "YOUTUBE_CLIENT_SECRET": client_secret.strip(),
        "YOUTUBE_REFRESH_TOKEN": refresh_token.strip(),
    }

    lines = []
    updated_keys = set()

    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")

        for line in content.splitlines():
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

    if not lines or not any(
        line.startswith("#") for line in lines[:3]
    ):
        header = [
            "# Credenciais YouTube (geradas via --youtube-auth)",
            "",
        ]
        lines = header + lines

    env_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    for key, value in values.items():
        os.environ[key] = value

    return env_path


def run_interactive_oauth(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    env_path: Path = ENV_FILE,
) -> CredentialStatus:
    """
    Executa fluxo OAuth interativo para obter refresh token.

    Abre o navegador, captura authorization code e salva no .env.
    """

    print("\n🔐 Configuração OAuth do YouTube\n")

    creds = get_env_credentials()

    client_id = (client_id or creds["client_id"]).strip()
    client_secret = (client_secret or creds["client_secret"]).strip()

    if _is_placeholder(client_id):
        print(
            "O Client ID não está configurado.\n"
            "Obtenha em: https://console.cloud.google.com/apis/credentials\n"
        )
        client_id = input("YOUTUBE_CLIENT_ID: ").strip()

    if _is_placeholder(client_secret):
        client_secret = input("YOUTUBE_CLIENT_SECRET: ").strip()

    if not client_id or not client_secret:
        status = CredentialStatus(
            configured=False,
            valid=False,
            messages=[
                "❌ Client ID e Client Secret são obrigatórios",
            ],
        )
        print(status.summary())
        return status

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        status = CredentialStatus(
            configured=False,
            valid=False,
            messages=[
                "❌ google-auth-oauthlib não instalado. "
                "Execute: pip install google-auth-oauthlib",
            ],
        )
        print(status.summary())
        return status

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    print(
        "\n🌐 Abrindo navegador para autorização...\n"
        "Faça login com a conta do canal YouTube e conceda as permissões.\n"
    )

    flow = InstalledAppFlow.from_client_config(
        client_config,
        scopes=YOUTUBE_SCOPES,
    )

    credentials = flow.run_local_server(
        port=0,
        prompt="consent",
        access_type="offline",
    )

    refresh_token = credentials.refresh_token

    if not refresh_token:
        status = CredentialStatus(
            configured=False,
            valid=False,
            messages=[
                "❌ Refresh token não retornado pelo Google.",
                "   Revogue o acesso em "
                "https://myaccount.google.com/permissions",
                "   e execute novamente: python main.py --youtube-auth",
            ],
        )
        print(status.summary())
        return status

    env_file = save_credentials_to_env(
        client_id,
        client_secret,
        refresh_token,
        env_path=env_path,
    )

    print(f"\n✅ Credenciais salvas em: {env_file.resolve()}\n")

    return validate_credentials(test_connection=True)
