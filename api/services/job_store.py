"""
Armazenamento persistente de jobs — JSON em output/jobs.json + eventos asyncio.

Jobs sobrevivem a restarts/redeploys quando output/ está em volume persistente.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional
from uuid import UUID

from api.models.schemas import JobStatus, SceneResult, SceneStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobStore:
    """
    Persistência de jobs em output/jobs.json.

    Também gerencia asyncio.Event por (job_id, scene_id) para notificação
    in-process quando um callback de cena é recebido.
    """

    def __init__(self, store_path: Path | str | None = None) -> None:
        if store_path is None:
            store_path = Path(__file__).resolve().parents[2] / "output" / "jobs.json"
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._scene_events: dict[str, asyncio.Event] = {}
        self._legacy_db_path = (
            Path(__file__).resolve().parents[2] / "database" / "pipeline_jobs.db"
        )
        self._ensure_store()

    def _ensure_store(self) -> None:
        with self._lock:
<<<<<<< HEAD
            if self.store_path.exists():
                return
            migrated = self._migrate_from_sqlite()
            if not migrated:
                self._write_all({})

    def _read_all(self) -> dict[str, dict[str, Any]]:
        if not self.store_path.exists():
            return {}
        try:
            raw = json.loads(self.store_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return raw if isinstance(raw, dict) else {}

    def _write_all(self, data: dict[str, dict[str, Any]]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.store_path.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(self.store_path)

    def _migrate_from_sqlite(self) -> bool:
        """Importa jobs legados de database/pipeline_jobs.db, se existir."""

        if not self._legacy_db_path.exists():
            return False

        conn = None
        try:
            conn = sqlite3.connect(str(self._legacy_db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM jobs").fetchall()
        except sqlite3.Error:
            return False
        finally:
            if conn is not None:
=======
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
            finally:
>>>>>>> 9e31449727825f390659d3d72a228a8bae937a04
                conn.close()

        if not rows:
            return False

        data: dict[str, dict[str, Any]] = {}
        for row in rows:
            data[row["job_id"]] = {
                "job_id": row["job_id"],
                "status": row["status"],
                "output_path": row["output_path"],
                "error_message": row["error_message"],
                "metadata": json.loads(row["metadata"] or "{}"),
                "scenes": json.loads(row["scenes"] or "{}"),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }

        self._write_all(data)
        return True

    def _mutate(self, job_id: UUID, mutator: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            data = self._read_all()
            key = str(job_id)
            record = data.get(key)
            if record is None:
                raise KeyError(f"Job {job_id} not found")
            mutator(record)
            record["updated_at"] = _utcnow().isoformat()
            data[key] = record
            self._write_all(data)

    def create_job(self, job_id: UUID, metadata: dict[str, Any] | None = None) -> None:
        """Registra um novo job com status queued."""

        now = _utcnow().isoformat()
        with self._lock:
            data = self._read_all()
            data[str(job_id)] = {
                "job_id": str(job_id),
                "status": JobStatus.QUEUED.value,
                "output_path": None,
                "error_message": None,
                "metadata": metadata or {},
                "scenes": {},
                "created_at": now,
                "updated_at": now,
            }
            self._write_all(data)

    def update_job_status(
        self,
        job_id: UUID,
        status: JobStatus,
        output_path: Optional[str] = None,
        error_message: Optional[str] = None,
        stdout_tail: Optional[str] = None,
    ) -> None:
        """Atualiza status geral do job de pipeline."""
<<<<<<< HEAD

        def _apply(record: dict[str, Any]) -> None:
            record["status"] = status.value
            if output_path is not None:
                record["output_path"] = output_path
            if error_message is not None:
                record["error_message"] = error_message

        self._mutate(job_id, _apply)
=======
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
>>>>>>> 9e31449727825f390659d3d72a228a8bae937a04

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

        def _apply(record: dict[str, Any]) -> None:
            scenes = record.setdefault("scenes", {})
            scenes[scene_id] = {
                "scene_id": scene_id,
                "status": status.value,
                "video_path": video_path,
                "provider_used": provider_used,
                "error_message": error_message,
                "updated_at": now,
            }

        self._mutate(job_id, _apply)

        event_key = self._scene_event_key(job_id, scene_id)
        event = self._scene_events.get(event_key)
        if event is not None:
            event.set()

    def get_job(self, job_id: UUID) -> Optional[dict[str, Any]]:
        """Retorna registro completo do job ou None."""

        record = self._read_all().get(str(job_id))
        if record is None:
            return None
        return self._record_to_dict(record)

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
    def _record_to_dict(record: dict[str, Any]) -> dict[str, Any]:
        scenes_raw = record.get("scenes") or {}
        scenes = {
            sid: SceneResult(**data)
            for sid, data in scenes_raw.items()
        }
        return {
<<<<<<< HEAD
            "job_id": UUID(record["job_id"]),
            "status": JobStatus(record["status"]),
            "output_path": record.get("output_path"),
            "error_message": record.get("error_message"),
            "metadata": record.get("metadata") or {},
=======
            "job_id": UUID(row["job_id"]),
            "status": JobStatus(row["status"]),
            "output_path": row["output_path"],
            "error_message": row["error_message"],
            "stdout_tail": row["stdout_tail"] if "stdout_tail" in row.keys() else None,
            "metadata": json.loads(row["metadata"] or "{}"),
>>>>>>> 9e31449727825f390659d3d72a228a8bae937a04
            "scenes": scenes,
            "created_at": datetime.fromisoformat(record["created_at"]),
            "updated_at": datetime.fromisoformat(record["updated_at"]),
        }


# Singleton compartilhado entre routers e serviços
job_store = JobStore()
