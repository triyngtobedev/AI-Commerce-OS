"""
Estado resumível do pipeline de produção.

Persiste progresso em pipeline_state.json por vídeo.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

PIPELINE_VERSION = "1.0.0"

STAGE_ORDER = [
    "collect",
    "analysis",
    "strategy",
    "script",
    "timeline",
    "media",
    "audio",
    "render",
    "export",
    "validate",
    "upload",
    "manifest",
    "report",
]

STATE_FILENAME = "pipeline_state.json"


class PipelineState:
    """Gerencia estado resumível do pipeline."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self._path = output_dir / STATE_FILENAME
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            with open(self._path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, dict):
                    return data

        now = datetime.now(timezone.utc).isoformat()
        return {
            "pipeline_version": PIPELINE_VERSION,
            "started_at": now,
            "updated_at": now,
            "current_step": None,
            "completed_steps": [],
            "step_timings": {},
            "step_errors": {},
            "providers_used": [],
            "status": "in_progress",
        }

    def save(self):
        self._data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as handle:
            json.dump(self._data, handle, ensure_ascii=False, indent=2)

    @property
    def completed_steps(self) -> list[str]:
        return list(self._data.get("completed_steps", []))

    def is_completed(self, stage: str) -> bool:
        return stage in self.completed_steps

    def should_skip(self, stage: str) -> bool:
        return self.is_completed(stage)

    def mark_started(self, stage: str):
        self._data["current_step"] = stage
        self.save()

    def mark_completed(self, stage: str, elapsed_seconds: float, *, extra: Optional[dict] = None):
        completed = self._data.setdefault("completed_steps", [])
        if stage not in completed:
            completed.append(stage)

        self._data.setdefault("step_timings", {})[stage] = round(elapsed_seconds, 3)
        self._data["current_step"] = stage

        if extra:
            for key, value in extra.items():
                self._data[key] = value

        self.save()

    def mark_failed(self, stage: str, error: str):
        self._data.setdefault("step_errors", {})[stage] = {
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._data["status"] = "failed"
        self.save()

    def mark_finished(self):
        self._data["status"] = "completed"
        self._data["current_step"] = None
        self.save()

    def get_resume_stage(self) -> Optional[str]:
        """Retorna primeira etapa não concluída."""

        for stage in STAGE_ORDER:
            if not self.is_completed(stage):
                return stage
        return None

    def add_provider(self, provider: str):
        providers = self._data.setdefault("providers_used", [])
        if provider and provider not in providers:
            providers.append(provider)
            self.save()

    def to_dict(self) -> dict:
        return dict(self._data)

    def save_artifact(self, filename: str, data: Any):
        """Salva artefato JSON da etapa."""

        path = self.output_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, default=str)

    def load_artifact(self, filename: str) -> Optional[Any]:
        path = self.output_dir / filename
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
