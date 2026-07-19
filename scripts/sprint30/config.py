"""Feature flags e paths do Sprint 30."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_METRICS_PATH = ROOT / "database" / "sprint_30_metrics.jsonl"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in ("1", "true", "yes", "on")


def is_sprint30_enabled() -> bool:
    return _env_bool("SPRINT30", default=False)


def is_footage_first() -> bool:
    if not is_sprint30_enabled():
        return False
    return _env_bool("FOOTAGE_FIRST", default=True)


def is_retention_controller_enabled() -> bool:
    if not is_sprint30_enabled():
        return False
    return _env_bool("RETENTION_CONTROLLER", default=True)


def get_metrics_path() -> Path:
    raw = os.getenv("SPRINT30_METRICS_PATH", "").strip()
    if raw:
        return Path(raw)
    return DEFAULT_METRICS_PATH


def get_flags() -> dict[str, bool]:
    return {
        "SPRINT30": is_sprint30_enabled(),
        "FOOTAGE_FIRST": is_footage_first(),
        "RETENTION_CONTROLLER": is_retention_controller_enabled(),
    }
