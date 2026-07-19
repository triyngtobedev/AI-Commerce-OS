"""
Controle central de quota Gemini — compartilhado entre router e chamadas multimodais Sprint 30.
"""

from __future__ import annotations

import threading
from typing import Any, Optional

_quota_exhausted = False
_lock = threading.Lock()

STAGES = ("visual_score", "thumbnail", "text_generation")


def is_gemini_quota_exhausted() -> bool:
    return _quota_exhausted


def mark_gemini_quota_exhausted(error: Optional[Exception] = None) -> None:
    global _quota_exhausted
    with _lock:
        _quota_exhausted = True
    detail = f": {error}" if error else ""
    print(f"[Gemini] Quota esgotada — usando fallback{detail}")


def is_daily_quota_exhausted(error: Exception) -> bool:
    return "limit: 0" in str(error).lower()


def is_quota_error(error: Exception) -> bool:
    msg = str(error).lower()
    if is_daily_quota_exhausted(error):
        return True
    return any(
        token in msg
        for token in (
            "429",
            "quota",
            "resource_exhausted",
            "rate limit",
            "too many requests",
        )
    )


def handle_gemini_error(error: Exception, *, stage: str) -> None:
    if is_daily_quota_exhausted(error):
        mark_gemini_quota_exhausted(error)
    elif is_quota_error(error):
        print(f"[Gemini/{stage}] Quota/rate limit: {error}")


def record_gemini_call(
    *,
    stage: str,
    model: str,
    fallback: bool = False,
) -> None:
    with _lock:
        metrics = _get_metrics_unlocked()
        metrics["total_calls"] += 1
        by_stage = metrics["calls_by_stage"]
        by_stage[stage] = by_stage.get(stage, 0) + 1
        by_model = metrics["calls_by_model"]
        by_model[model] = by_model.get(model, 0) + 1
        if fallback:
            metrics["quota_fallbacks"] += 1


def get_gemini_metrics() -> dict[str, Any]:
    with _lock:
        return _snapshot_unlocked()


def reset_gemini_metrics(*, reset_quota: bool = False) -> None:
    global _quota_exhausted
    with _lock:
        if reset_quota:
            _quota_exhausted = False
        _metrics_store.clear()
        _metrics_store.update(_empty_metrics())


def _empty_metrics() -> dict[str, Any]:
    return {
        "total_calls": 0,
        "calls_by_stage": {stage: 0 for stage in STAGES},
        "calls_by_model": {},
        "quota_fallbacks": 0,
        "quota_exhausted": False,
    }


_metrics_store: dict[str, Any] = _empty_metrics()


def _get_metrics_unlocked() -> dict[str, Any]:
    return _metrics_store


def _snapshot_unlocked() -> dict[str, Any]:
    metrics = _get_metrics_unlocked()
    return {
        "gemini_total_calls": metrics["total_calls"],
        "gemini_calls_by_stage": dict(metrics["calls_by_stage"]),
        "gemini_calls_by_model": dict(metrics["calls_by_model"]),
        "gemini_quota_fallbacks": metrics["quota_fallbacks"],
        "gemini_quota_exhausted": _quota_exhausted,
    }
