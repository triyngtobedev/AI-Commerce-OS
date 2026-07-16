"""
Geração do production_manifest.json — fonte oficial de auditoria.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from scripts.core.production.hash_utils import hash_file, hash_files
from scripts.core.production.pipeline_state import PIPELINE_VERSION


MANIFEST_FILENAME = "production_manifest.json"


def _collect_assets(output_dir: Path, result: Dict[str, Any]) -> list[dict]:
    assets = []
    candidates = []

    video = result.get("video")
    if video:
        candidates.append(Path(video))

    audio = result.get("audio")
    if audio:
        candidates.append(Path(audio))

    thumb = result.get("youtube_metadata", {}).get("thumbnail")
    if thumb:
        candidates.append(Path(str(thumb)))

    subtitle = result.get("subtitle_file")
    if subtitle:
        candidates.append(Path(subtitle))

    assets_dir = output_dir / "assets"
    if assets_dir.exists():
        for path in assets_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in (".mp4", ".jpg", ".jpeg", ".png", ".webp", ".mp3"):
                candidates.append(path)

    seen = set()
    for path in candidates:
        if not path.exists():
            continue
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        assets.append({
            "path": str(path),
            "hash": hash_file(path),
            "size_bytes": path.stat().st_size,
        })

    return assets


def generate_production_manifest(
    output_dir: Path,
    result: Dict[str, Any],
    *,
    pipeline_state: Optional[dict] = None,
    upload_result: Optional[dict] = None,
    providers_used: Optional[list] = None,
    performance_report: Optional[dict] = None,
) -> Path:
    """
    Gera production_manifest.json com todos os metadados de auditoria.
    """

    conteudo = result.get("conteudo", {}) or {}
    produto = result.get("produto", {}) or {}
    youtube_meta = result.get("youtube_metadata", {}) or {}

    key_files = [
        output_dir / "analysis.json",
        output_dir / "strategy.json",
        output_dir / "script.json",
        output_dir / "scenes.json",
        output_dir / "video_final.mp4",
        output_dir / "post_package.json",
    ]
    existing_files = [p for p in key_files if p.exists()]

    manifest = {
        "schema_version": "1.0",
        "pipeline_version": PIPELINE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "produto": {
            "nome": produto.get("nome", ""),
            "categoria": produto.get("categoria", ""),
        },
        "tema": produto.get("nome", ""),
        "titulo": conteudo.get("titulo", ""),
        "descricao": conteudo.get("descricao", ""),
        "tags": conteudo.get("tags", []),
        "roteiro": result.get("roteiro", {}),
        "timeline": {
            "cenas": result.get("cenas", {}),
            "asset_queries": result.get("asset_queries", []),
        },
        "assets_utilizados": _collect_assets(output_dir, result),
        "providers_utilizados": providers_used or (pipeline_state or {}).get("providers_used", []),
        "duracao": conteudo.get("duracao"),
        "thumbnail": youtube_meta.get("thumbnail"),
        "step_timings": (pipeline_state or {}).get("step_timings", {}),
        "file_hashes": hash_files(existing_files),
        "upload": upload_result,
        "performance": performance_report,
        "status": (pipeline_state or {}).get("status", "completed"),
    }

    path = output_dir / MANIFEST_FILENAME
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)

    return path
