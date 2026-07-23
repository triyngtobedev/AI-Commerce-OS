"""
Armazenamento persistente de jobs — SQLite + eventos asyncio para callbacks.

Mantém status de pipelines e resultados de cenas geradas via n8n.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from api.models.schemas import JobStatus, SceneResult, SceneStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobStore:
    """
    Persistência simples de jobs em SQLite.

    Também gerencia asyncio.Event por (job_id, scene_id) para notificação
    in-process quando um callback de cena é recebido.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            env_path = os.getenv("DATABASE_PATH", "").strip()
            if env_path:
                db_path = Path(env_path)
            else:
                db_path = Path(__file__).resolve().parents[2] / "database" / "pipeline_jobs.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._scene_events: dict[str, asyncio.Event] = {}
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS jobs (
                        job_id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        output_path TEXT,
                        error_message TEXT,
                        stdout_tail TEXT,
                        metadata TEXT,
                        scenes TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    """
                )
                try:
                    conn.execute("ALTER TABLE jobs ADD COLUMN stdout_tail TEXT")
                except sqlite3.OperationalError:
                    pass
                conn.commit()
            except sqlite3.DatabaseError:
                # Banco corrompido (ex: disco cheio durante escrita) — recria
                conn.close()
                self.db_path.unlink(missing_ok=True)
                conn = self._connect()
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS jobs (
                        job_id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        output_path TEXT,
                        error_message TEXT,
                        stdout_tail TEXT,
                        metadata TEXT,
                        scenes TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def create_job(self, job_id: UUID, metadata: dict[str, Any] | None = None) -> None:
        """Registra um novo job com status queued."""
        now = _utcnow().isoformat()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO jobs (job_id, status, metadata, scenes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(job_id),
                        JobStatus.QUEUED.value,
                        json.dumps(metadata or {}),
                        json.dumps({}),
                        now,
                        now,
                    ),
                )
                conn.commit()
            except sqlite3.DatabaseError:
                conn.close()
                self.db_path.unlink(missing_ok=True)
                conn = self._connect()
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS jobs (
                        job_id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        output_path TEXT,
                        error_message TEXT,
                        stdout_tail TEXT,
                        metadata TEXT,
                        scenes TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    """
                )
                conn.execute(
                    """
                    INSERT INTO jobs (job_id, status, metadata, scenes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(job_id),
                        JobStatus.QUEUED.value,
                        json.dumps(metadata or {}),
                        json.dumps({}),
                        now,
                        now,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def update_job_status(
        self,
        job_id: UUID,
        status: JobStatus,
        output_path: Optional[str] = None,
        error_message: Optional[str] = None,
        stdout_tail: Optional[str] = None,
    ) -> None:
        """Atualiza status geral do job de pipeline."""
        now = _utcnow().isoformat()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = ?, output_path = COALESCE(?, output_path),
                        error_message = COALESCE(?, error_message),
                        stdout_tail = COALESCE(?, stdout_tail),
                        updated_at = ?
                    WHERE job_id = ?
                    """,
                    (
                        status.value,
                        output_path,
                        error_message,
                        stdout_tail,
                        now,
                        str(job_id),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def update_scene(
        self,
        job_id: UUID,
        scene_id: str,
        status: SceneStatus,
        video_path: Optional[str] = None,
        provider_used: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Atualiza resultado de uma cena e dispara evento de notificação."""
        now = _utcnow().isoformat()
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT scenes FROM jobs WHERE job_id = ?",
                    (str(job_id),),
                ).fetchone()
                if row is None:
                    raise KeyError(f"Job {job_id} not found")

                scenes: dict[str, Any] = json.loads(row["scenes"] or "{}")
                scenes[scene_id] = {
                    "scene_id": scene_id,
                    "status": status.value,
                    "video_path": video_path,
                    "provider_used": provider_used,
                    "error_message": error_message,
                    "updated_at": now,
                }
                conn.execute(
                    "UPDATE jobs SET scenes = ?, updated_at = ? WHERE job_id = ?",
                    (json.dumps(scenes), now, str(job_id)),
                )
                conn.commit()
            finally:
                conn.close()

        # Notifica waiters in-process (asyncio.Event)
        event_key = self._scene_event_key(job_id, scene_id)
        event = self._scene_events.get(event_key)
        if event is not None:
            event.set()

    def mark_running_as_failed(self) -> list[str]:
        """Marca todos os jobs 'running' como 'failed' (boot recovery)."""
        affected: list[str] = []
        now = _utcnow().isoformat()
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT job_id FROM jobs WHERE status = ?",
                    (JobStatus.RUNNING.value,),
                ).fetchall()
                for row in rows:
                    affected.append(str(row["job_id"]))
                conn.execute(
                    """
                    UPDATE jobs SET status = ?, error_message = ?, updated_at = ?
                    WHERE status = ?
                    """,
                    (
                        JobStatus.FAILED.value,
                        "container_restart: job interrompido por reinicialização do servidor",
                        now,
                        JobStatus.RUNNING.value,
                    ),
                )
                conn.commit()
            except sqlite3.DatabaseError:
                pass
            finally:
                conn.close()
        return affected

    def has_running_job(self) -> bool:
        """True se existe algum job com status running."""
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT 1 FROM jobs WHERE status = ? LIMIT 1",
                    (JobStatus.RUNNING.value,),
                ).fetchone()
                return row is not None
            finally:
                conn.close()

    def list_all_jobs(self) -> list[dict[str, Any]]:
        """Lista últimos 20 jobs ordenados por created_at desc."""
        with self._lock:
            conn = self._connect()
            try:
                cursor = conn.execute(
                    "SELECT job_id, status, error_message, created_at, updated_at "
                    "FROM jobs ORDER BY created_at DESC LIMIT 20"
                )
                rows = cursor.fetchall()
                return [
                    {
                        "job_id": r[0],
                        "status": r[1],
                        "error_message": r[2],
                        "created_at": r[3],
                        "updated_at": r[4],
                    }
                    for r in rows
                ]
            finally:
                conn.close()

    def get_job(self, job_id: UUID) -> Optional[dict[str, Any]]:
        """Retorna registro completo do job ou None."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (str(job_id),),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_dict(row)
        finally:
            conn.close()

    def get_scene(self, job_id: UUID, scene_id: str) -> Optional[SceneResult]:
        """Retorna resultado de uma cena específica."""
        job = self.get_job(job_id)
        if not job:
            return None
        scenes = job.get("scenes", {})
        data = scenes.get(scene_id)
        if not data:
            return None
        return SceneResult(**data)

    def wait_event(self, job_id: UUID, scene_id: str) -> asyncio.Event:
        """Obtém ou cria asyncio.Event para aguardar callback de cena."""
        event_key = self._scene_event_key(job_id, scene_id)
        if event_key not in self._scene_events:
            self._scene_events[event_key] = asyncio.Event()
        else:
            self._scene_events[event_key].clear()
        return self._scene_events[event_key]

    def clear_scene_event(self, job_id: UUID, scene_id: str) -> None:
        """Remove evento de cena da memória após conclusão."""
        event_key = self._scene_event_key(job_id, scene_id)
        self._scene_events.pop(event_key, None)

    @staticmethod
    def _scene_event_key(job_id: UUID, scene_id: str) -> str:
        return f"{job_id}:{scene_id}"

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        scenes_raw = json.loads(row["scenes"] or "{}")
        scenes = {sid: SceneResult(**data) for sid, data in scenes_raw.items()}
        return {
            "job_id": UUID(row["job_id"]),
            "status": JobStatus(row["status"]),
            "output_path": row["output_path"],
            "error_message": row["error_message"],
            "stdout_tail": row["stdout_tail"] if "stdout_tail" in row.keys() else None,
            "metadata": json.loads(row["metadata"] or "{}"),
            "scenes": scenes,
            "created_at": datetime.fromisoformat(row["created_at"]),
            "updated_at": datetime.fromisoformat(row["updated_at"]),
        }


# Singleton compartilhado entre routers e serviços
job_store = JobStore()
