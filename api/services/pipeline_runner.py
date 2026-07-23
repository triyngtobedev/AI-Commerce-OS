"""
Executor de pipeline — invoca main.py como subprocess assíncrono.

Não altera main.py; apenas monta argumentos CLI compatíveis e monitora saída.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path
from uuid import UUID

from api.models.schemas import JobStatus, PipelineRunRequest
from api.services.job_store import job_store
from scripts.youtube.template_override import ENV_ROTEIRO_TEMPLATE

# Raiz do projeto (dois níveis acima de api/services/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_PY = PROJECT_ROOT / "main.py"

# main.py não expõe --output-dir; o path final vem do log de render_video_project:
# scripts/video/renderer.py → "🎬 Vídeo final criado: {output}"
FINAL_VIDEO_LOG_PATTERN = re.compile(
    r"(?:🎬 Vídeo final criado:\s+|PIPELINE_OUTPUT_VIDEO=)"
    r"(?P<path>.+\.(?:mp4|webm))",
    re.IGNORECASE,
)

# Marcadores de falha no stdout — usados para diagnóstico quando exit code é 0
_FAILURE_STDOUT_MARKERS = (
    "❌ Pipeline concluiu sem produzir vídeo final.",
    "❌ Vídeo não criado",
    "❌ Erro no render:",
    "❌ Falha total",
    "Nenhuma API de IA disponível",
    "❌ Nenhum tema encontrado",
    "❌ Nenhum tema novo",
    "❌ Erro processando",
    "Vídeos gerados: 0",
    "Vídeos com arquivo final: 0",
    "[Lofi] Nenhum footage disponível",
    "Sem mídia para cena",
    "Pipeline interrompido",
    "Etapa '",
    "Resposta de roteiro inválida",
)


def _extract_failure_reason(stdout: str, stderr: str) -> str | None:
    """Extrai a linha de erro mais relevante do stdout/stderr."""
    for line in reversed(stdout.splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        if any(marker in stripped for marker in _FAILURE_STDOUT_MARKERS):
            return stripped

    for line in reversed(stderr.splitlines()):
        stripped = line.strip()
        if stripped:
            return stripped

    return None

# Linhas de stdout persistidas no job para diagnóstico via GET /pipeline/status
JOB_STDOUT_TAIL_LINES = 100

# Marcadores do AI Router — sempre incluídos no trecho retornado pelo job
_AI_ROUTER_MARKERS = (
    "[AI Router]",
    "[Groq/",
    "[OpenRouter]",
    "❌ Falha total",
    "Nenhuma API de IA disponível",
    "⚠️ Gemini indisponível",
    "⚠️ Groq indisponível",
)


def build_cli_args(request: PipelineRunRequest) -> list[str]:
    """
    Converte PipelineRunRequest em argumentos CLI para main.py.

    Apenas flags suportadas nativamente por main.py são incluídas.
    """
    args = [sys.executable, str(MAIN_PY)]

    if request.platform:
        args.extend(["--platform", request.platform])
    if request.production:
        args.append("--production")
    if request.research:
        args.append("--research")
    if request.upload:
        args.append("--upload")
    if request.privacy:
        args.extend(["--privacy", request.privacy])
    if request.max_videos is not None:
        args.extend(["--max-videos", str(request.max_videos)])
    if request.force or request.topic:
        args.append("--force")

    return args


async def run_pipeline_subprocess(job_id: UUID, request: PipelineRunRequest) -> None:
    """
    Executa main.py em background e atualiza job_store com o resultado.

    Marca o job como running → completed/failed conforme exit code e stdout.
    """
    # Lock de concorrência: só um job por vez
    if job_store.has_running_job():
        job_store.update_job_status(
            job_id,
            JobStatus.FAILED,
            error_message=(
                "Já existe um job em execução. "
                "O pipeline atual suporta apenas um job por vez. "
                "Aguarde o job atual terminar antes de disparar outro."
            ),
        )
        return

    job_store.update_job_status(job_id, JobStatus.RUNNING)
    cli_args = build_cli_args(request)

    env = os.environ.copy()
    env["PIPELINE_JOB_ID"] = str(job_id)
    # topic/language não têm flag CLI em main.py — repassados via env para integrações
    if request.topic:
        env["PIPELINE_TOPIC_OVERRIDE"] = str(request.topic)
    if request.template:
        env[ENV_ROTEIRO_TEMPLATE] = str(request.template)
    if request.language:
        env["PIPELINE_LANGUAGE"] = request.language
    for key, value in request.metadata.items():
        env[f"PIPELINE_META_{key.upper()}"] = str(value)

    try:
        process = await asyncio.create_subprocess_exec(
            *cli_args,
            cwd=str(PROJECT_ROOT),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=900
            )
        except asyncio.TimeoutError:
            process.kill()
            stdout_bytes, stderr_bytes = await process.communicate()
            job_store.update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message="Pipeline excedeu 15 minutos — subprocesso encerrado",
            )
            return
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        _emit_subprocess_logs(job_id, stdout, stderr)
        stdout_excerpt = _stdout_for_job(stdout)

        if process.returncode == 0:
            try:
                output_path = _resolve_output_path(stdout, request)
            except ValueError as exc:
                reason = _extract_failure_reason(stdout, stderr)
                diagnostic = _failure_diagnostic(stdout, stderr)
                error_msg = str(exc)
                if reason:
                    error_msg = f"{error_msg}\nCausa provável: {reason}"
                job_store.update_job_status(
                    job_id,
                    JobStatus.FAILED,
                    error_message=f"{error_msg}\n\n{diagnostic}"[:4000],
                    stdout_tail=stdout_excerpt,
                )
            else:
                job_store.update_job_status(
                    job_id,
                    JobStatus.COMPLETED,
                    output_path=output_path,
                    stdout_tail=stdout_excerpt,
                )
        else:
            reason = _extract_failure_reason(stdout, stderr)
            diagnostic = _failure_diagnostic(stdout, stderr)
            error_msg = reason or f"Exit code {process.returncode}"
            if diagnostic:
                error_msg = f"{error_msg}\n\n{diagnostic}"
            job_store.update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=error_msg[:4000],
                stdout_tail=stdout_excerpt,
            )
    except Exception as exc:
        job_store.update_job_status(
            job_id,
            JobStatus.FAILED,
            error_message=str(exc),
        )

    # Auto-cleanup: remove arquivos intermediários, mantém vídeo final + reports
    _cleanup_job_output(job_id)


def _cleanup_job_output(job_id: UUID) -> None:
    """Remove diretórios intermediários do job, mantém video_final.mp4 e reports."""
    job = job_store.get_job(job_id)
    if not job:
        return
    output_path = job.get("output_path")
    if not output_path:
        return

    output_dir = Path(output_path).parent
    if not output_dir.exists():
        return

    # Mantém estes arquivos
    keep_patterns = {"video_final.mp4", "thumbnail.jpg", "*.json", "*.srt", "*.ass"}
    # Remove estes diretórios (intermediários)
    remove_dirs = [
        output_dir / "assets" / "scene_clips",
        output_dir / "dark_channel_work",
        output_dir / "assets" / "videos",
        output_dir / "assets" / "images",
        output_dir / "assets" / "audio",
    ]

    for d in remove_dirs:
        if d.exists():
            try:
                import shutil
                shutil.rmtree(d)
            except Exception:
                pass


def _stderr_tail(stderr: str, lines: int = 20) -> str:
    """Retorna as últimas N linhas do stderr para diagnóstico de falhas."""
    if not stderr.strip():
        return ""
    return "\n".join(stderr.strip().splitlines()[-lines:])


def _stdout_tail(stdout: str, lines: int = JOB_STDOUT_TAIL_LINES) -> str:
    """Retorna as últimas N linhas do stdout para diagnóstico."""
    if not stdout.strip():
        return ""
    return "\n".join(stdout.strip().splitlines()[-lines:])


def _extract_ai_router_lines(stdout: str) -> list[str]:
    """Extrai linhas do AI Router presentes no stdout completo."""
    return [
        line
        for line in stdout.splitlines()
        if any(marker in line for marker in _AI_ROUTER_MARKERS)
    ]


def _stdout_for_job(stdout: str) -> str:
    """
    Monta trecho de stdout para persistir no job.

    Usa as últimas JOB_STDOUT_TAIL_LINES linhas e garante que o resultado
    final do AI Router (provider usado ou falha total) apareça no excerpt.
    """
    tail = _stdout_tail(stdout)
    if not tail:
        return ""

    router_lines = _extract_ai_router_lines(stdout)
    if not router_lines:
        return tail

    tail_line_set = set(tail.splitlines())
    missing_router = [line for line in router_lines if line not in tail_line_set]
    if not missing_router:
        return tail

    router_excerpt = "\n".join(router_lines[-30:])
    return f"{tail}\n\n--- AI Router (garantido) ---\n{router_excerpt}"


def _emit_subprocess_logs(job_id: UUID, stdout: str, stderr: str) -> None:
    """Replica stdout/stderr do pipeline nos logs do Railway (uvicorn stdout)."""
    prefix = f"[pipeline {job_id}]"
    if stdout.strip():
        print(f"{prefix} --- stdout ---", flush=True)
        print(stdout, flush=True)
    if stderr.strip():
        print(f"{prefix} --- stderr ---", flush=True)
        print(stderr, flush=True)


def _failure_diagnostic(stdout: str, stderr: str) -> str:
    """Monta trecho de log útil quando o subprocess falha ou termina sem vídeo."""
    parts: list[str] = []
    out_tail = _stdout_for_job(stdout)
    err_tail = _stderr_tail(stderr, lines=JOB_STDOUT_TAIL_LINES)
    if out_tail:
        parts.append("--- stdout (últimas linhas) ---")
        parts.append(out_tail)
    if err_tail:
        parts.append("--- stderr (últimas linhas) ---")
        parts.append(err_tail)
    if not parts:
        parts.append("(subprocess sem stdout/stderr)")
    return "\n".join(parts)


def _resolve_output_path(stdout: str, request: PipelineRunRequest) -> str:
    """
    Determina o caminho do vídeo final após o subprocess.

    main.py não aceita --output-dir; extrai do stdout o log emitido por
    render_video_project: "🎬 Vídeo final criado: <path>".
    """
    for line in stdout.splitlines():
        match = FINAL_VIDEO_LOG_PATTERN.search(line)
        if not match:
            continue
        raw_path = match.group("path").strip().strip("'\"")
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        if candidate.exists():
            return str(candidate.resolve())
        raise ValueError(
            f"Pipeline logou vídeo em '{raw_path}' mas o arquivo não existe"
        )

    output_roots: list[Path] = []
    if request.platform in ("youtube_dark", "all"):
        output_roots.append(PROJECT_ROOT / "output" / "youtube_dark")
    if request.platform in ("tiktok_shop", "all"):
        output_roots.append(PROJECT_ROOT / "output")

    candidates: list[Path] = []
    for root in output_roots:
        if root.exists():
            candidates.extend(root.rglob("video_final.mp4"))

    if candidates:
        newest = max(candidates, key=lambda p: p.stat().st_mtime)
        return str(newest.resolve())

    raise ValueError(
        "Não foi possível determinar o vídeo final. "
        "Formato esperado no stdout: '🎬 Vídeo final criado: <caminho>.mp4' "
        "ou 'PIPELINE_OUTPUT_VIDEO=<caminho>.mp4' "
        "(scripts/video/renderer.py::render_video_project). "
        "Fallback: nenhum video_final.mp4 encontrado em output/."
    )
