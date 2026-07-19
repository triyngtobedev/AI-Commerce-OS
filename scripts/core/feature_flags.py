"""
Feature flags Sprint 30 — toggles editoriais sem mudança de arquitetura.

Todas as flags respeitam SPRINT30_ENABLED como master switch.
Valores: true/false, 1/0, yes/no, on/off (case-insensitive).
"""

from __future__ import annotations

import os


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    normalized = value.strip().lower()
    if normalized in ("1", "true", "yes", "on"):
        return True
    if normalized in ("0", "false", "no", "off"):
        return False
    return default


def _flag(name: str, *, default: bool = True) -> bool:
    return _parse_bool(os.getenv(name), default)


def sprint30_enabled() -> bool:
    return _flag("SPRINT30_ENABLED", default=True)


def sprint30_visual_score() -> bool:
    return sprint30_enabled() and _flag("SPRINT30_VISUAL_SCORE", default=True)


def sprint30_thumbnail_ab() -> bool:
    return sprint30_enabled() and _flag("SPRINT30_THUMBNAIL_AB", default=True)


def sprint30_audio_layer() -> bool:
    return sprint30_enabled() and _flag("SPRINT30_AUDIO_LAYER", default=True)


def sprint30_retention_controller() -> bool:
    retention = os.getenv("SPRINT30_RETENTION")
    controller = os.getenv("SPRINT30_RETENTION_CONTROLLER")
    if retention is not None and retention.strip():
        enabled = sprint30_enabled() and _parse_bool(retention, default=True)
    else:
        enabled = sprint30_enabled() and _flag("SPRINT30_RETENTION_CONTROLLER", default=True)
    return enabled


def sprint30_metrics() -> bool:
    return sprint30_enabled() and _flag("SPRINT30_METRICS", default=True)


def sprint30_flags_snapshot() -> dict[str, bool]:
    return {
        "SPRINT30_ENABLED": sprint30_enabled(),
        "SPRINT30_VISUAL_SCORE": sprint30_visual_score(),
        "SPRINT30_THUMBNAIL_AB": sprint30_thumbnail_ab(),
        "SPRINT30_AUDIO_LAYER": sprint30_audio_layer(),
        "SPRINT30_RETENTION": sprint30_retention_controller(),
        "SPRINT30_RETENTION_CONTROLLER": sprint30_retention_controller(),
        "SPRINT30_METRICS": sprint30_metrics(),
    }
