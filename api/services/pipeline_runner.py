"""
Executor de pipeline — executa pipeline in-process (thread) para evitar
problemas de pipe/stdio no Railway.
"""

from __future__ import annotations

import asyncio
import io
import os
import re
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from uuid import UUID

from api.models.schemas import JobStatus, PipelineRunRequest
from api.services.job_store import job_store

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# main.py não expõe --output-dir; o path final vem do log de render_video_project:
# scripts/video/renderer.py → "🎬 Vídeo final criado: {output}"
FINAL_VIDEO_LOG_PATTERN = re.compile(
    r"(?:🎬 Vídeo final criado:\s+|PIPELINE_OUTPUT_VIDEO=)"
    r"(?P<path>.+\.(?:mp4|webm))",
    re.IGNORECASE,
)

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


async def run_pipeline_subprocess(job_id: UUID, request: PipelineRunRequest) -> None:
    """
    Executa pipeline YouTube in-process (numa thread) e atualiza job_store.

    Evita subprocesso — que estava travando sem stdout no Railway.
    """
    if job_store.has_running_job():
        job_store.update_job_status(
            job_id,
            JobStatus.FAILED,
            error_message="Já existe um job em execução.",
        )
        return

    job_store.update_job_status(job_id, JobStatus.RUNNING)

    def _run():
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            try:
                os.environ["PIPELINE_JOB_ID"] = str(job_id)
                if request.topic:
                    os.environ["PIPELINE_TOPIC_OVERRIDE"] = str(request.topic)
                if request.template:
                    os.environ["YOUTUBE_ROTEIRO_TEMPLATE"] = str(request.template)
                if request.language:
                    os.environ["PIPELINE_LANGUAGE"] = str(request.language)

                from scripts.pipeline.youtube_pipeline import run_youtube_pipeline
                from scripts.publisher.youtube_publish_config import resolve_upload_visibility

                max_videos = request.max_videos or 1
                auto_upload = request.upload or request.production
                privacy, _ = resolve_upload_visibility(cli_privacy=request.privacy)

                results = run_youtube_pipeline(
                    auto_research=request.research or request.production,
                    max_videos=max_videos,
                    auto_upload=auto_upload,
                    privacy_status=privacy,
                    production_mode=request.production,
                    force=request.force or bool(request.topic),
                )

                videos = sum(1 for r in results if r.get("video"))
                if request.platform in ("youtube_dark",) and videos == 0:
                    print("❌ Pipeline concluiu sem produzir vídeo final.")
            except Exception:
                traceback.print_exc()
        return buf.getvalue()

    try:
        loop = asyncio.get_running_loop()
        stdout = await asyncio.wait_for(
            loop.run_in_executor(None, _run), timeout=1800
        )
    except asyncio.TimeoutError:
        job_store.update_job_status(
            job_id,
            JobStatus.FAILED,
            error_message="Pipeline excedeu 30 minutos — execução encerrada",
        )
        return

    stdout_excerpt = _stdout_for_job(stdout)
    _emit_subprocess_logs(job_id, stdout, "")

    if "❌ Pipeline concluiu sem produzir vídeo final." in stdout:
        job_store.update_job_status(
            job_id,
            JobStatus.FAILED,
            error_message="Pipeline não produziu vídeo final",
            stdout_tail=stdout_excerpt,
        )
    else:
        try:
            output_path = _resolve_output_path(stdout, request)
            job_store.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                output_path=output_path,
                stdout_tail=stdout_excerpt,
            )
        except ValueError:
            job_store.update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message="Pipeline executou mas vídeo final não encontrado",
                stdout_tail=stdout_excerpt,
            )

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

    # Safety: nunca remove o diretório raiz do job, só subpastas temporárias
    remove_dirs = [
        output_dir / "assets" / "scene_clips",
        output_dir / "dark_channel_work",
        output_dir / "assets" / "videos",
        output_dir / "assets" / "images",
        output_dir / "assets" / "audio",
    ]

    import shutil
    for d in remove_dirs:
        if d.exists() and d != output_dir:
            try:
                shutil.rmtree(d)
                print(f"[Cleanup] Removido: {d.name}")
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
