#!/usr/bin/env python3
"""Configura n8n local: owner, credencial API, workflows e ativação."""

from __future__ import annotations

import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"
WORKFLOWS_DIR = INFRA / "n8n_workflows"
ENV_MAIN = ROOT / ".env"
ENV_N8N = INFRA / ".env.n8n"

N8N_BASE = os.getenv("N8N_BASE_URL", "http://localhost:5678")
OWNER_EMAIL = os.getenv("N8N_OWNER_EMAIL", "admin@local.dev")
OWNER_PASSWORD = os.getenv("N8N_OWNER_PASSWORD", "n8nLocal!2026")
OWNER_FIRST = os.getenv("N8N_OWNER_FIRST", "Admin")
OWNER_LAST = os.getenv("N8N_OWNER_LAST", "Local")


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


def unwrap(body: dict | list | str | None) -> dict | list | str | None:
    if isinstance(body, dict) and "data" in body and len(body) <= 2:
        return body["data"]
    return body


class N8nClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
    ) -> tuple[int, dict | list | str | None]:
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                parsed = json.loads(raw) if raw else None
                return resp.status, parsed
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                parsed = raw
            return exc.code, parsed


def setup_owner(client: N8nClient) -> None:
    status, body = client.request(
        "POST",
        "/rest/owner/setup",
        {
            "email": OWNER_EMAIL,
            "firstName": OWNER_FIRST,
            "lastName": OWNER_LAST,
            "password": OWNER_PASSWORD,
        },
    )
    if status in (200, 201):
        print("Owner criado e autenticado.")
        return
    if status == 400 and "already" in str(body).lower():
        print("Owner já existe — fazendo login...")
    else:
        print(f"Setup owner: HTTP {status} — {body}")

    status, body = client.request(
        "POST",
        "/rest/login",
        {"emailOrLdapLoginId": OWNER_EMAIL, "password": OWNER_PASSWORD},
    )
    if status != 200:
        raise RuntimeError(f"Login falhou: HTTP {status} — {body}")
    print("Login ok.")


CREDENTIAL_SPECS: tuple[tuple[str, str, str], ...] = (
    # (nome credencial n8n, header name, valor ou template com {value})
    ("Pipeline API Key", "X-API-Key", "{value}"),
    ("Replicate API Token", "Authorization", "Token {value}"),
    ("Hugging Face API Token", "Authorization", "Bearer {value}"),
)


def create_header_auth_credential(
    client: N8nClient,
    name: str,
    header_name: str,
    header_value: str,
) -> str:
    status, body = client.request("GET", "/rest/credentials")
    if status == 200:
        items = unwrap(body)
        if isinstance(items, list):
            for cred in items:
                if cred.get("name") == name:
                    cred_id = cred["id"]
                    patch_status, patch_body = client.request(
                        "PATCH",
                        f"/rest/credentials/{cred_id}",
                        {
                            "name": name,
                            "type": "httpHeaderAuth",
                            "data": {"name": header_name, "value": header_value},
                        },
                    )
                    if patch_status == 200:
                        print(f"Credencial atualizada: {name} ({cred_id})")
                    else:
                        print(f"Credencial existente: {name} ({cred_id})")
                    return cred_id

    status, body = client.request(
        "POST",
        "/rest/credentials",
        {
            "name": name,
            "type": "httpHeaderAuth",
            "data": {"name": header_name, "value": header_value},
        },
    )
    if status not in (200, 201):
        raise RuntimeError(f"Criar credencial {name} falhou: HTTP {status} — {body}")
    cred = unwrap(body)
    if not isinstance(cred, dict) or "id" not in cred:
        raise RuntimeError(f"Resposta inesperada ao criar credencial {name}: {body}")
    print(f"Credencial criada: {name} ({cred['id']})")
    return cred["id"]


def ensure_credentials(client: N8nClient, env_main: dict[str, str]) -> dict[str, str]:
    """Cria credenciais HTTP Header exigidas pelos workflows."""
    cred_ids: dict[str, str] = {}

    pipeline_key = resolve_api_key(env_main)
    if not pipeline_key:
        raise RuntimeError("PIPELINE_API_KEY ou CLOUD_API_KEY ausente em .env")

    cred_ids["Pipeline API Key"] = create_header_auth_credential(
        client,
        "Pipeline API Key",
        "X-API-Key",
        pipeline_key,
    )

    replicate_token = env_main.get("REPLICATE_API_TOKEN", "")
    if replicate_token:
        cred_ids["Replicate API Token"] = create_header_auth_credential(
            client,
            "Replicate API Token",
            "Authorization",
            f"Token {replicate_token}",
        )
    else:
        print("⚠️ REPLICATE_API_TOKEN ausente — configure para workflow free tier Replicate")

    hf_token = env_main.get("HF_API_TOKEN") or env_main.get("HF_TOKEN", "")
    if hf_token:
        cred_ids["Hugging Face API Token"] = create_header_auth_credential(
            client,
            "Hugging Face API Token",
            "Authorization",
            f"Bearer {hf_token}",
        )
    else:
        print("⚠️ HF_API_TOKEN ausente — fallback HF Router ficará indisponível no n8n")

    return cred_ids


def patch_workflow_urls(wf: dict, api_base: str) -> dict:
    """
    Substitui $env.PIPELINE_API_BASE_URL pela URL literal.

    n8n 2.x bloqueia $env nas expressões por padrão. URLs de polling usam
    URL estática + {{ }} (sem prefixo = antes de https — evita 'Invalid URL').
    """
    base = api_base.rstrip("/")
    env_prefix = "={{ $env.PIPELINE_API_BASE_URL }}"

    def patch_url(value: str) -> str:
        if "/pipeline/status/" in value:
            return (
                f"{base}/api/v1/pipeline/status/"
                "{{ $('POST Pipeline Run').first().json.job_id }}"
            )

        if value.startswith(env_prefix):
            return f"{base}{value[len(env_prefix):]}"

        if "$env.PIPELINE_API_BASE_URL" in value:
            return value.replace("$env.PIPELINE_API_BASE_URL", base)

        return value

    def walk(obj: object) -> object:
        if isinstance(obj, dict):
            return {key: walk(val) for key, val in obj.items()}
        if isinstance(obj, list):
            return [walk(item) for item in obj]
        if isinstance(obj, str):
            return patch_url(obj)
        return obj

    patched = walk(wf)
    if not isinstance(patched, dict):
        raise RuntimeError("patch_workflow_urls: workflow inválido após patch")
    return patched


PLACEHOLDER_CREDENTIAL_SUFFIX = "_CREDENTIAL_ID"


def patch_workflow_optional_nodes(wf: dict) -> dict:
    """
    Desativa nós com credenciais placeholder (Slack opcional, etc.).

    Evita falha em execução quando SLACK_CREDENTIAL_ID não foi configurado.
    """
    patched = json.loads(json.dumps(wf))
    disabled: list[str] = []

    for node in patched.get("nodes", []):
        creds = node.get("credentials") or {}
        has_template_cred = any(
            isinstance(meta, dict)
            and str(meta.get("id", "")).endswith(PLACEHOLDER_CREDENTIAL_SUFFIX)
            for meta in creds.values()
        )
        notes = node.get("notes") or ""
        is_placeholder = "PLACEHOLDER" in notes or "(opcional)" in node.get("name", "").lower()

        if node.get("disabled") or has_template_cred or (is_placeholder and creds):
            node["disabled"] = True
            node.pop("credentials", None)
            disabled.append(node.get("name", node.get("id", "?")))

    if disabled:
        print(f"  Nós opcionais desativados (sem credencial): {', '.join(disabled)}")

    return patched


def patch_workflow_credentials(workflow: dict, cred_ids: dict[str, str]) -> dict:
    wf = json.loads(json.dumps(workflow))
    for node in wf.get("nodes", []):
        creds = node.get("credentials")
        if not creds:
            continue
        for cred_type in creds:
            cred_name = creds[cred_type].get("name")
            if cred_name and cred_name in cred_ids:
                creds[cred_type]["id"] = cred_ids[cred_name]
    return wf


def import_workflow(
    client: N8nClient,
    workflow_path: Path,
    cred_ids: dict[str, str],
    api_base: str,
) -> str:
    raw = json.loads(workflow_path.read_text(encoding="utf-8"))
    wf = patch_workflow_urls(raw, api_base)
    wf = patch_workflow_credentials(wf, cred_ids)
    wf = patch_workflow_optional_nodes(wf)

    payload = {
        "name": wf["name"],
        "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": wf.get("settings", {}),
        "staticData": wf.get("staticData"),
    }

    status, body = client.request("GET", "/rest/workflows")
    existing_id: str | None = None
    duplicate_ids: list[str] = []
    if status == 200 and wf["name"].startswith("02 — Scene Generation Orchestrator"):
        items = unwrap(body)
        if isinstance(items, list):
            for item in items:
                if item.get("name") == wf["name"]:
                    existing_id = item["id"]
                elif item.get("name", "").startswith("02 — Scene Generation Orchestrator"):
                    duplicate_ids.append(item["id"])
    elif status == 200:
        items = unwrap(body)
        if isinstance(items, list):
            for item in items:
                if item.get("name") == wf["name"]:
                    existing_id = item["id"]
                    break

    for dup_id in duplicate_ids:
        if dup_id != existing_id:
            client.request("POST", f"/rest/workflows/{dup_id}/deactivate", {})
            client.request("DELETE", f"/rest/workflows/{dup_id}")
            print(f"Workflow legado removido: {dup_id}")

    if existing_id:
        status, body = client.request("PATCH", f"/rest/workflows/{existing_id}", payload)
        if status != 200:
            raise RuntimeError(f"Atualizar workflow falhou: HTTP {status} — {body}")
        print(f"Workflow atualizado: {existing_id}")
        return existing_id

    status, body = client.request("POST", "/rest/workflows", payload)
    if status not in (200, 201):
        raise RuntimeError(f"Importar workflow falhou: HTTP {status} — {body}")
    created = unwrap(body)
    if not isinstance(created, dict) or "id" not in created:
        raise RuntimeError(f"Resposta inesperada ao importar workflow: {body}")
    wf_id = created["id"]
    print(f"Workflow importado: {wf_id}")
    return wf_id


def activate_workflow(client: N8nClient, wf_id: str, name: str) -> None:
    status, body = client.request("GET", f"/rest/workflows/{wf_id}")
    if status != 200:
        raise RuntimeError(f"Obter workflow {wf_id} falhou: HTTP {status} — {body}")

    data = unwrap(body)
    if not isinstance(data, dict):
        raise RuntimeError(f"Resposta inesperada ao obter workflow {wf_id}: {body}")

    version_id = data.get("versionId")
    if not version_id:
        raise RuntimeError(f"Workflow {wf_id} sem versionId — impossível ativar")

    status, body = client.request(
        "POST",
        f"/rest/workflows/{wf_id}/activate",
        {"versionId": version_id},
    )
    if status not in (200, 201):
        raise RuntimeError(f"Ativar workflow {wf_id} falhou: HTTP {status} — {body}")

    print(f"Workflow ativado: {wf_id}")


def resolve_api_key(env_main: dict[str, str]) -> str:
    """
    Chave para chamar o Railway (cliente).

    Mesma ordem de gerar_video.py: CLOUD_API_KEY → PIPELINE_API_KEY.
    """
    cloud = env_main.get("CLOUD_API_KEY", "").strip()
    pipeline = env_main.get("PIPELINE_API_KEY", "").strip()
    if cloud and pipeline and cloud != pipeline:
        print(
            "⚠️ CLOUD_API_KEY e PIPELINE_API_KEY diferem no .env — "
            "usando CLOUD_API_KEY (mesma lógica do gerar_video.py)"
        )
        return cloud
    return cloud or pipeline


def resolve_pipeline_api_url(
    env_main: dict[str, str],
    env_n8n: dict[str, str] | None = None,
) -> str:
    """Prioriza CLOUD_API_URL (Railway) → PIPELINE_API_BASE_URL → localhost."""
    for source in (env_main, env_n8n or {}):
        for key in ("CLOUD_API_URL", "PIPELINE_API_BASE_URL"):
            value = source.get(key, "").strip()
            if value:
                return value.rstrip("/")
    return "http://127.0.0.1:8000"


def test_pipeline(api_key: str, api_base: str) -> None:
    payload = json.dumps({"platform": "youtube_dark", "topic": "teste n8n setup"}).encode("utf-8")
    url = f"{api_base.rstrip('/')}/api/v1/pipeline/run"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            print(f"Pipeline teste OK ({api_base}): {result}")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        print(f"Pipeline teste HTTP {exc.code} ({api_base}): {raw}")
        if exc.code == 401:
            print(
                "\n  ERRO 401 — chave local não bate com o Railway.\n"
                "  1. Abra railway.app → Variables → copie PIPELINE_API_KEY\n"
                "  2. Cole no .env do PC em CLOUD_API_KEY e PIPELINE_API_KEY (mesmo valor)\n"
                "  3. Rode .\\infra\\ativar-n8n.ps1 de novo\n"
            )
    except urllib.error.URLError as exc:
        print(f"Pipeline teste falhou ({api_base}): {exc.reason}")
        print("  → Confira se o Railway está Active ou se a FastAPI local está rodando.")


def main() -> int:
    env_main = load_env(ENV_MAIN)
    env_n8n = load_env(ENV_N8N)
    api_key = resolve_api_key(env_main)
    if not api_key:
        print("PIPELINE_API_KEY ou CLOUD_API_KEY ausente em .env", file=sys.stderr)
        return 1

    api_base = resolve_pipeline_api_url(env_main, env_n8n)
    print(f"n8n: {N8N_BASE}")
    print(f"Pipeline API: {api_base}")
    client = N8nClient(N8N_BASE)
    setup_owner(client)
    cred_ids = ensure_credentials(client, env_main)

    wf_files = sorted(
        p for p in WORKFLOWS_DIR.glob("*.json") if p.name != "notification_nodes.json"
    )
    if not wf_files:
        print("Nenhum workflow em infra/n8n_workflows/", file=sys.stderr)
        return 1

    wf_ids: dict[str, str] = {}
    for path in wf_files:
        wf_ids[path.name] = import_workflow(client, path, cred_ids, api_base)

    for path in wf_files:
        raw = json.loads(path.read_text(encoding="utf-8"))
        activate_workflow(client, wf_ids[path.name], raw["name"])

    print("\nTestando pipeline via API...")
    test_pipeline(api_key, api_base)

    print("\nConcluído.")
    print(f"  n8n UI:       {N8N_BASE}")
    print(f"  Login n8n:    {OWNER_EMAIL} / {OWNER_PASSWORD}")
    print(f"  Pipeline API: {api_base}")
    print(f"  Guia:         docs/ATIVAR-N8N.md")
    return 0


def validate_railway_connection(env_main: dict[str, str]) -> bool:
    """Valida conexão com Railway via health check."""
    api_base = resolve_pipeline_api_url(env_main)
    api_key = resolve_api_key(env_main)
    url = f"{api_base.rstrip('/')}/api/v1/health"
    print(f"\nValidando Railway: {url}")
    try:
        req = urllib.request.Request(url, headers={"X-API-Key": api_key} if api_key else {})
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
            print(f"  OK — HTTP 200 | auth_configured={body.get('auth_configured')}")
            if body.get("persistent_storage"):
                print("  Volume persistente: montado")
            return True
    except urllib.error.HTTPError as exc:
        print(f"  ERRO HTTP {exc.code}")
        return False
    except urllib.error.URLError as exc:
        print(f"  ERRO de conexão: {exc.reason}")
        return False


def validate_youtube_oauth() -> None:
    """Verifica presença de credenciais YouTube."""
    env_youtube = ROOT / ".env.youtube"
    print("\nYouTube OAuth:")
    if not env_youtube.exists():
        print("  .env.youtube não encontrado")
        print("  Execute: python scripts/youtube/gerar_token.py")
        return
    env = load_env(env_youtube)
    for var in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"):
        status = "OK" if env.get(var) else "ausente"
        print(f"  {var}: {status}")


def run_validate_only() -> int:
    env_main = load_env(ENV_MAIN)
    ok_railway = validate_railway_connection(env_main)
    validate_youtube_oauth()
    return 0 if ok_railway else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--validate", "-v"):
        raise SystemExit(run_validate_only())
    raise SystemExit(main())
