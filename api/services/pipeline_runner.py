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

# Raiz do projeto (dois níveis acima de api/services/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_PY = PROJECT_ROOT / "main.py"

# main.py não expõe --output-dir; o path final vem do log de render_video_project:
# scripts/video/renderer.py → "🎬 Vídeo final criado: {output}"
FINAL_VIDEO_LOG_PATTERN = re.compile(
    r"🎬 Vídeo final criado:\s+(?P<path>.+\.(?:mp4|webm))",
    re.IGNORECASE,
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
    if request.force:
        args.append("--force")

    return args


async def run_pipeline_subprocess(job_id: UUID, request: PipelineRunRequest) -> None:
    """
    Executa main.py em background e atualiza job_store com o resultado.

    Marca o job como running → completed/failed conforme exit code e stdout.
    """
    job_store.update_job_status(job_id, JobStatus.RUNNING)
    cli_args = build_cli_args(request)

    env = os.environ.copy()
    env["PIPELINE_JOB_ID"] = str(job_id)
    # topic/language não têm flag CLI em main.py — repassados via env para integrações
    if request.topic:
        env["PIPELINE_TOPIC_OVERRIDE"] = str(request.topic)
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
        stdout_bytes, stderr_bytes = await process.communicate()
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        if process.returncode == 0:
            try:
                output_path = _resolve_output_path(stdout, request)
            except ValueError as exc:
                job_store.update_job_status(
                    job_id,
                    JobStatus.FAILED,
                    error_message=str(exc)[:4000],
                )
            else:
                job_store.update_job_status(
                    job_id,
                    JobStatus.COMPLETED,
                    output_path=output_path,
                )
        else:
            stderr_tail = _stderr_tail(stderr)
            error_msg = (
                stderr_tail
                or stdout.strip()
                or f"Exit code {process.returncode}"
            )
            job_store.update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=error_msg[:4000],
            )
    except Exception as exc:
        job_store.update_job_status(
            job_id,
            JobStatus.FAILED,
            error_message=str(exc),
        )


def _stderr_tail(stderr: str, lines: int = 20) -> str:
    """Retorna as últimas N linhas do stderr para diagnóstico de falhas."""
    if not stderr.strip():
        return ""
    return "\n".join(stderr.strip().splitlines()[-lines:])


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
        "(scripts/video/renderer.py::render_video_project). "
        "Fallback: nenhum video_final.mp4 encontrado em output/."
    )
