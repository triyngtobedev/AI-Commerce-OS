"""
Smoke test end-to-end do Railway.

Uso:
  python scripts/cloud/smoke_test_railway.py
  python scripts/cloud/smoke_test_railway.py --url https://meu-app.railway.app
  python scripts/cloud/smoke_test_railway.py --url https://meu-app.railway.app --key minha-api-key

Variáveis de ambiente alternativas:
  RAILWAY_URL, PIPELINE_API_KEY ou CLOUD_API_KEY
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any


GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def fail(msg: str) -> None:
    print(f"  {RED}✗{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}!{RESET} {msg}")


def section(title: str) -> None:
    print(f"\n{BOLD}{title}{RESET}")
    print("─" * 50)


@dataclass
class CheckResult:
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def http_get(url: str, headers: dict | None = None, timeout: int = 15) -> tuple[int, Any]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8")
            try:
                return r.status, json.loads(body)
            except json.JSONDecodeError:
                return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, str(e)


def http_post(
    url: str, payload: dict, headers: dict | None = None, timeout: int = 30
) -> tuple[int, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8")
            try:
                return r.status, json.loads(body)
            except json.JSONDecodeError:
                return r.status, body
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8")
            return e.code, json.loads(body)
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, str(e)


def check_health(base_url: str, result: CheckResult) -> bool:
    section("1. Health check")
    status, body = http_get(f"{base_url}/api/v1/health")

    if status == 200:
        ok(f"GET /api/v1/health → {status}")
        if isinstance(body, dict):
            auth_ok = body.get("auth_configured", False)
            if auth_ok:
                ok(f"auth_configured: {auth_ok}")
                result.passed.append("health + auth_configured")
            else:
                warn("auth_configured: false — verifique PIPELINE_API_KEY no Railway")
                result.warnings.append("auth_configured=false")

            git = body.get("git_commit", "desconhecido")
            ok(f"Commit em produção: {git}")

            if body.get("persistent_storage"):
                ok("persistent_storage: true")
                result.passed.append("volume persistente montado")
            else:
                warn("persistent_storage: false — configure volume em /app/persistent")
                result.warnings.append("persistent_storage=false")
        return True

    fail(f"GET /api/v1/health → {status} (esperado 200)")
    result.failed.append(f"health retornou {status}")
    return False


def check_auth(base_url: str, api_key: str, result: CheckResult) -> None:
    section("2. Autenticação")

    status, _ = http_get(f"{base_url}/api/v1/pipeline/status/test-id")
    if status in (401, 403):
        ok(f"Sem chave → {status} (bloqueado corretamente)")
        result.passed.append("rejeita requisição sem chave")
    else:
        fail(f"Sem chave → {status} (esperado 401/403) — endpoint desprotegido!")
        result.failed.append("endpoint não protegido por auth")

    status, _ = http_get(
        f"{base_url}/api/v1/pipeline/status/test-id",
        {"X-API-Key": "chave-errada"},
    )
    if status in (401, 403):
        ok(f"Chave inválida → {status} (rejeitada corretamente)")
        result.passed.append("rejeita chave inválida")
    else:
        warn(f"Chave inválida → {status}")

    if api_key:
        status, _ = http_get(
            f"{base_url}/api/v1/pipeline/status/job-inexistente",
            {"X-API-Key": api_key},
        )
        if status in (200, 404):
            ok(f"Chave correta → {status} (aceita)")
            result.passed.append("aceita chave válida")
        else:
            fail(f"Chave correta → {status} (esperado 200/404)")
            result.failed.append(f"chave válida recusada com {status}")
    else:
        warn("PIPELINE_API_KEY não fornecida — pulando teste com chave válida")
        result.warnings.append("api_key não testada")


def check_job_submission(base_url: str, api_key: str, result: CheckResult) -> str | None:
    section("3. Submissão de job")

    if not api_key:
        warn("Sem API key — pulando submissão de job")
        result.warnings.append("job não testado sem api_key")
        return None

    status, body = http_post(
        f"{base_url}/api/v1/pipeline/run",
        {"topic": "smoke-test-ci", "template": "documentario"},
        {"X-API-Key": api_key},
    )

    if status in (200, 202):
        job_id = body.get("job_id") if isinstance(body, dict) else None
        ok(f"POST /pipeline/run → {status} | job_id: {job_id}")
        result.passed.append("job submetido com sucesso")
        return job_id

    fail(f"POST /pipeline/run → {status}: {body}")
    result.failed.append(f"falha ao submeter job: {status}")
    return None


def check_job_status(base_url: str, api_key: str, job_id: str, result: CheckResult) -> None:
    section("4. Polling de status do job")

    headers = {"X-API-Key": api_key}
    print(f"  Aguardando job {job_id}...")

    for attempt in range(1, 7):
        time.sleep(5)
        status, body = http_get(f"{base_url}/api/v1/pipeline/status/{job_id}", headers)

        if status != 200:
            warn(f"  Tentativa {attempt}: status HTTP {status}")
            continue

        job_status = body.get("status", "?") if isinstance(body, dict) else "?"
        stdout_tail = body.get("stdout_tail", "") if isinstance(body, dict) else ""

        print(f"  [{attempt}] job status: {job_status}")

        if job_status in ("completed", "failed", "error"):
            if job_status == "completed":
                ok(f"Job concluído: {job_status}")
                result.passed.append("job completou com sucesso")
            else:
                warn(f"Job encerrou com: {job_status}")
                if stdout_tail:
                    print(f"\n  stdout_tail:\n{'─'*40}")
                    for line in stdout_tail.strip().split("\n")[-10:]:
                        print(f"  {line}")
                    print("─" * 40)
                result.warnings.append(f"job encerrou com {job_status}")
            return

    warn("Job ainda em andamento após 30s — isso é normal para vídeos longos")
    result.warnings.append("job não concluiu no tempo do smoke test")


def check_lofi_dark(base_url: str, api_key: str, result: CheckResult) -> None:
    section("5. Template lofi_dark")

    if not api_key:
        warn("Sem API key — pulando teste de template")
        return

    status, body = http_post(
        f"{base_url}/api/v1/pipeline/run",
        {"topic": "smoke-lofi", "template": "lofi_dark"},
        {"X-API-Key": api_key},
    )

    if status in (200, 202):
        ok(f"Template lofi_dark aceito → job_id: {body.get('job_id', '?')}")
        result.passed.append("template lofi_dark aceito pela API")
    else:
        warn(f"Template lofi_dark → {status}: {body}")
        result.warnings.append("lofi_dark pode não estar disponível no Railway")


def print_summary(result: CheckResult) -> int:
    section("Resumo")
    print(f"  {GREEN}Passou:{RESET}    {len(result.passed)}")
    print(f"  {YELLOW}Avisos:{RESET}    {len(result.warnings)}")
    print(f"  {RED}Falhou:{RESET}    {len(result.failed)}")

    if result.failed:
        print(f"\n{RED}Itens com falha:{RESET}")
        for item in result.failed:
            print(f"  • {item}")

    if result.warnings:
        print(f"\n{YELLOW}Avisos:{RESET}")
        for item in result.warnings:
            print(f"  • {item}")

    if not result.failed:
        print(f"\n{GREEN}{BOLD}Railway OK — pronto para produção.{RESET}\n")
        return 0

    print(f"\n{RED}{BOLD}Smoke test falhou — corrija os itens acima.{RESET}\n")
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test do Railway para ai-commerce-os")
    parser.add_argument("--url", default=os.getenv("RAILWAY_URL", ""), help="URL base do Railway")
    parser.add_argument(
        "--key",
        default=os.getenv("PIPELINE_API_KEY") or os.getenv("CLOUD_API_KEY", ""),
        help="API key",
    )
    parser.add_argument("--skip-job", action="store_true", help="Pular submissão de job (mais rápido)")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    if not base_url:
        print(f"{RED}Erro: informe --url ou defina RAILWAY_URL no ambiente.{RESET}")
        print("  Exemplo: python scripts/cloud/smoke_test_railway.py --url https://meu-app.railway.app")
        sys.exit(1)

    print(f"\n{BOLD}Smoke test Railway — ai-commerce-os{RESET}")
    print(f"URL: {base_url}")
    print(f"API key: {'configurada' if args.key else 'NÃO configurada (testes de auth limitados)'}")

    result = CheckResult()

    healthy = check_health(base_url, result)
    if not healthy:
        print(f"\n{RED}API não está respondendo. Verifique o deploy no Railway.{RESET}\n")
        sys.exit(1)

    check_auth(base_url, args.key, result)

    if not args.skip_job:
        job_id = check_job_submission(base_url, args.key, result)
        if job_id:
            check_job_status(base_url, args.key, job_id, result)
        check_lofi_dark(base_url, args.key, result)

    sys.exit(print_summary(result))


if __name__ == "__main__":
    main()
