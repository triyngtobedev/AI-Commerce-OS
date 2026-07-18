#!/usr/bin/env python3
"""
Upload automático de vídeos para o YouTube.

Entry point usado pelo pipeline (Railway) e pela API HTTP (n8n).
Lê metadados de script.json / youtube_package.json e publica video_final.mp4.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from scripts.analytics.video_registry import register_video
from scripts.publisher.youtube_publish_config import resolve_upload_visibility
from scripts.publisher.youtube_uploader import UPLOAD_STATUS, upload_from_folder


def _load_script_metadata(folder: Path) -> Dict[str, Any]:
    """Carrega metadados de script.json e youtube_package.json."""
    metadata: Dict[str, Any] = {}

    script_file = folder / "script.json"
    if script_file.exists():
        with open(script_file, "r", encoding="utf-8") as file:
            script = json.load(file)
        metadata["topic"] = script.get("tema") or script.get("topic") or ""
        metadata["template"] = script.get("template") or script.get("formato") or ""
        metadata["title"] = script.get("titulo") or script.get("title") or ""

    package_file = folder / "youtube_package.json"
    if package_file.exists():
        with open(package_file, "r", encoding="utf-8") as file:
            package = json.load(file)
        metadata.setdefault("title", package.get("titulo", ""))
        metadata.setdefault("topic", package.get("produto", ""))

    return metadata


def upload_video_folder(
    folder: Path | str,
    *,
    privacy_status: Optional[str] = None,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Faz upload do vídeo final de uma pasta de output do pipeline.

    Args:
        folder: Pasta com video_final.mp4 e youtube_package.json
        privacy_status: private | unlisted | public (padrão: UPLOAD_VISIBILITY ou unlisted)
        job_id: ID do job Railway (opcional, para rastreamento)

    Returns:
        Resultado do upload com video_id, url e status
    """
    folder_path = Path(folder)

    if privacy_status is None:
        privacy_status, _ = resolve_upload_visibility()

    print(f"[YouTube Uploader] Pasta: {folder_path}")
    print(f"[YouTube Uploader] Privacidade: {privacy_status}")

    result = upload_from_folder(folder_path, privacy_status=privacy_status)

    if result.get("status") == UPLOAD_STATUS["uploaded"]:
        meta = _load_script_metadata(folder_path)
        registry = register_video(
            video_id=result["video_id"],
            video_url=result["url"],
            topic=str(meta.get("topic", "")),
            template=str(meta.get("template", "")),
            title=str(meta.get("title", "")),
            output_folder=str(folder_path.resolve()),
            job_id=job_id,
            privacy_status=privacy_status,
        )
        result["registry"] = registry
        print(f"[YouTube Uploader] Registrado em database/videos.json")
        print(f"[YouTube Uploader] Link: {result['url']}")

    return result


def upload_from_job_output(
    output_path: Path | str,
    *,
    privacy_status: Optional[str] = None,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Faz upload a partir do caminho do video_final.mp4 retornado pelo job.
    """
    video_path = Path(output_path)
    folder = video_path.parent if video_path.name == "video_final.mp4" else video_path

    if not (folder / "video_final.mp4").exists() and video_path.exists():
        folder = video_path.parent

    return upload_video_folder(
        folder,
        privacy_status=privacy_status,
        job_id=job_id,
    )


def main() -> int:
    """CLI: python scripts/youtube/uploader.py <pasta_output>"""
    if len(sys.argv) < 2:
        print("Uso: python scripts/youtube/uploader.py <pasta_output>")
        print("Exemplo: python scripts/youtube/uploader.py output/youtube_dark/meu-tema")
        return 1

    folder = Path(sys.argv[1])
    if not folder.exists():
        print(f"❌ Pasta não encontrada: {folder}")
        return 1

    result = upload_video_folder(folder)
    status = result.get("status", "UNKNOWN")

    if status == UPLOAD_STATUS["uploaded"]:
        print(f"✅ Upload concluído: {result.get('url')}")
        return 0

    print(f"❌ Upload falhou: {result.get('message', status)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
