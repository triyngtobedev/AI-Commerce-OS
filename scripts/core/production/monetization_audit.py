"""
Auditoria de qualidade para monetização.

Detecta repetição de assets, thumbnails, títulos, hooks e introduções.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from scripts.core.production.logger import get_logger
from scripts.metrics.metrics_tracker import _load_metrics


def _load_previous_manifests(output_base: Path = Path("output/youtube_dark")) -> List[dict]:
    manifests = []

    if not output_base.exists():
        return manifests

    for folder in output_base.iterdir():
        if not folder.is_dir():
            continue
        manifest_path = folder / "production_manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as handle:
                    manifests.append(json.load(handle))
            except (json.JSONDecodeError, OSError):
                continue

    return manifests


def _normalize(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _extract_hook(roteiro: dict) -> str:
    if not isinstance(roteiro, dict):
        return ""
    return _normalize(roteiro.get("hook", ""))


def _extract_intro(roteiro: dict) -> str:
    if not isinstance(roteiro, dict):
        return ""
    hook = roteiro.get("hook", "")
    contexto = roteiro.get("contexto", "")
    combined = f"{hook} {contexto}".strip()
    return _normalize(combined[:200])


def _collect_asset_hashes(manifest: dict) -> Set[str]:
    hashes: Set[str] = set()
    for asset in manifest.get("assets_utilizados", []):
        h = asset.get("hash")
        if h:
            hashes.add(h)
    return hashes


def run_monetization_audit(
    result: Dict[str, Any],
    output_dir: Path,
    *,
    lookback_manifests: Optional[List[dict]] = None,
) -> dict:
    """
    Audita risco de conteúdo repetitivo para monetização.
    """

    logger = get_logger("monetization_audit")

    if lookback_manifests is None:
        lookback_manifests = _load_previous_manifests()

    conteudo = result.get("conteudo", {}) or {}
    roteiro = result.get("roteiro", {}) or {}
    youtube_meta = result.get("youtube_metadata", {}) or {}

    current_title = _normalize(conteudo.get("titulo", ""))
    current_hook = _extract_hook(roteiro)
    current_intro = _extract_intro(roteiro)
    current_thumb = _normalize(str(youtube_meta.get("thumbnail", "")))

    alerts: List[dict] = []

    # Métricas históricas
    metrics = _load_metrics()
    published_titles = {
        _normalize(r.get("titulo", ""))
        for r in metrics
        if r.get("status") == "published" and r.get("titulo")
    }

    if current_title and current_title in published_titles:
        alerts.append({
            "type": "title_repetition",
            "severity": "high",
            "message": f"Título já publicado: '{conteudo.get('titulo', '')}'",
        })

    # Comparar com manifests anteriores
    for prev in lookback_manifests:
        prev_title = _normalize(prev.get("titulo", ""))
        if current_title and prev_title and current_title == prev_title:
            alerts.append({
                "type": "title_repetition",
                "severity": "high",
                "message": f"Título duplicado com produção anterior: '{prev.get('titulo', '')}'",
            })

        prev_hook = _extract_hook(prev.get("roteiro", {}))
        if current_hook and prev_hook and current_hook == prev_hook:
            alerts.append({
                "type": "hook_repetition",
                "severity": "medium",
                "message": "Hook idêntico a produção anterior",
            })

        prev_intro = _extract_intro(prev.get("roteiro", {}))
        if current_intro and prev_intro and current_intro == prev_intro:
            alerts.append({
                "type": "intro_repetition",
                "severity": "medium",
                "message": "Introdução (hook+contexto) idêntica a produção anterior",
            })

        prev_thumb = _normalize(str(prev.get("thumbnail", "")))
        if current_thumb and prev_thumb and current_thumb == prev_thumb:
            alerts.append({
                "type": "thumbnail_repetition",
                "severity": "medium",
                "message": "Thumbnail reutilizada de produção anterior",
            })

    # Asset repetition via hashes
    current_manifest_assets = _collect_asset_hashes({
        "assets_utilizados": [
            {"hash": h}
            for h in _collect_asset_hashes_from_result(result, output_dir)
        ],
    })

    for prev in lookback_manifests:
        prev_hashes = _collect_asset_hashes(prev)
        overlap = current_manifest_assets & prev_hashes
        if len(overlap) >= 3:
            alerts.append({
                "type": "asset_repetition",
                "severity": "high" if len(overlap) >= 5 else "medium",
                "message": f"{len(overlap)} assets reutilizados de produção anterior",
                "overlap_count": len(overlap),
            })

    report = {
        "risk_level": "high" if any(a["severity"] == "high" for a in alerts) else (
            "medium" if alerts else "low"
        ),
        "alerts": alerts,
        "alert_count": len(alerts),
    }

    path = output_dir / "monetization_audit.json"
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    if alerts:
        logger.warning(
            f"Auditoria de monetização: {len(alerts)} alerta(s) — risco {report['risk_level']}"
        )
    else:
        logger.success("Auditoria de monetização: sem alertas")

    return report


def _collect_asset_hashes_from_result(result: Dict[str, Any], output_dir: Path) -> Set[str]:
    from scripts.core.production.hash_utils import hash_file

    hashes: Set[str] = set()
    candidates = []

    for key in ("video", "audio", "subtitle_file"):
        val = result.get(key)
        if val:
            candidates.append(Path(val))

    assets_dir = output_dir / "assets"
    if assets_dir.exists():
        for path in assets_dir.rglob("*"):
            if path.is_file():
                candidates.append(path)

    for path in candidates:
        h = hash_file(path)
        if h:
            hashes.add(h)

    return hashes
