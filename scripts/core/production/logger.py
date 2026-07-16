"""
Logging padronizado para produção contínua.

Níveis: INFO, SUCCESS, WARNING, ERROR
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class LogLevel(str, Enum):
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"


_LEVEL_ICONS = {
    LogLevel.INFO: "ℹ️",
    LogLevel.SUCCESS: "✅",
    LogLevel.WARNING: "⚠️",
    LogLevel.ERROR: "❌",
}


class ProductionLogger:
    """Logger estruturado por etapa do pipeline."""

    def __init__(self, stage: str = "pipeline"):
        self.stage = stage
        self._entries: list[dict] = []

    def _emit(self, level: LogLevel, message: str, *, error: Optional[str] = None):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": self.stage,
            "level": level.value,
            "message": message,
        }
        if error:
            entry["error"] = error

        self._entries.append(entry)

        icon = _LEVEL_ICONS.get(level, "")
        line = f"[{level.value}] [{self.stage}] {icon} {message}"
        if error:
            line += f" — {error}"

        print(line, file=sys.stderr if level == LogLevel.ERROR else sys.stdout)

    def info(self, message: str):
        self._emit(LogLevel.INFO, message)

    def success(self, message: str):
        self._emit(LogLevel.SUCCESS, message)

    def warning(self, message: str):
        self._emit(LogLevel.WARNING, message)

    def error(self, message: str, *, error: Optional[str] = None):
        self._emit(LogLevel.ERROR, message, error=error)

    def stage_start(self):
        self.info(f"Início da etapa '{self.stage}'")

    def stage_end(self, elapsed_seconds: float, *, success: bool = True):
        msg = f"Fim da etapa '{self.stage}' — {elapsed_seconds:.2f}s"
        if success:
            self.success(msg)
        else:
            self.error(msg)

    def get_entries(self) -> list[dict]:
        return list(self._entries)


_loggers: dict[str, ProductionLogger] = {}


def get_logger(stage: str = "pipeline") -> ProductionLogger:
    if stage not in _loggers:
        _loggers[stage] = ProductionLogger(stage)
    return _loggers[stage]
