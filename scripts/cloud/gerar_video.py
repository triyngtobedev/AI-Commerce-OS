#!/usr/bin/env python3
"""
Cliente local — aciona geração de vídeo na nuvem e baixa o resultado.

O PC NÃO processa nada pesado: só envia o pedido, acompanha o status e baixa o MP4.

Uso:
    python scripts/cloud/gerar_video.py --topic "A verdade sobre a Biblioteca de Alexandria"
    python scripts/cloud/gerar_video.py --topic "Emus vs Austrália" --production
    python scripts/cloud/gerar_video.py --topic "O Mistério da Explosão de Tunguska" --template lofi_dark

Configure no .env local:
    CLOUD_API_URL=https://seu-app.up.railway.app
    CLOUD_API_KEY=<PIPELINE_API_KEY do Railway>
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_DOWNLOAD_DIR = PROJECT_ROOT / "downloads"


def _api_headers(api_key: str) -> dict[str, str]:
    return {"X-API-Key": api_key, "Content-Type": "application/json"}


def _check_health(base_url: str, api_key: str) -> None:
    url = f"{base_url.rstrip('/')}/api/v1/health"
    # (connect, read) — falha rápido se host inacessível; read curto pois /health é instantâneo
    response = requests.get(url, timeout=(5, 20))
    if response.status_code == 502:
        raise RuntimeError(
            "Servidor retornou 502 (Application failed to respond). "
            "O deploy pode estar verde mas a app não escuta na porta $PORT do Railway. "
            "Confira Deploy Logs e Settings → Networking → Target Port."
        )
    response.raise_for_status()
    data = response.json()
    print(f"✓ Servidor online — versão {data.get('version', '?')}")


def _start_job(
    base_url: str,
    api_key: str,
    *,
    topic: str | None,
    production: bool,
    platform: str,
    template: str | None = None,
) -> str:
    url = f"{base_url.rstrip('/')}/api/v1/pipeline/run"
    payload = {
        "platform": platform,
        "production": production,
        "max_videos": 1,
        "topic": topic,
    }
    if template:
        payload["template"] = template
    response = requests.post(
        url,
        json=payload,
        headers=_api_headers(api_key),
        timeout=30,
    )
    response.raise_for_status()
    job_id = response.json()["job_id"]
    print(f"→ Job enfileirado: {job_id}")
    return job_id


def _poll_status(
    base_url: str,
    api_key: str,
    job_id: str,
    *,
    interval: int = 30,
    timeout: int = 7200,
) -> dict:
    url = f"{base_url.rstrip('/')}/api/v1/pipeline/status/{job_id}"
    started = time.time()
    last_status = None

    while True:
        elapsed = int(time.time() - started)
        if elapsed > timeout:
            raise TimeoutError(
                f"Job não concluiu em {timeout}s. "
                f"Verifique os logs no painel Railway (Deploy Logs)."
            )

        response = requests.get(url, headers=_api_headers(api_key), timeout=30)
        if response.status_code == 404:
            raise RuntimeError(
                "O servidor foi reiniciado durante o job. Tente novamente."
            )
        response.raise_for_status()
        data = response.json()
        status = data["status"]

        if status != last_status:
            mins = elapsed // 60
            secs = elapsed % 60
            print(f"  [{mins:02d}:{secs:02d}] Status: {status}")
            last_status = status

        if status == "completed":
            return data
        if status == "failed":
            error = data.get("error_message") or "Erro desconhecido"
            raise RuntimeError(f"Pipeline falhou: {error}")

        time.sleep(interval)


def _download_video(
    base_url: str,
    api_key: str,
    job_id: str,
    dest_dir: Path,
) -> Path:
    url = f"{base_url.rstrip('/')}/api/v1/pipeline/download/{job_id}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    print("→ Baixando vídeo...")
    response = requests.get(
        url,
        headers=_api_headers(api_key),
        stream=True,
        timeout=600,
    )
    response.raise_for_status()

    filename = "video_final.mp4"
    disposition = response.headers.get("Content-Disposition", "")
    if "filename=" in disposition:
        filename = disposition.split("filename=")[-1].strip('"')

    dest_path = dest_dir / filename
    with open(dest_path, "wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 256):
            if chunk:
                handle.write(chunk)

    size_mb = dest_path.stat().st_size / (1024 * 1024)
    print(f"✓ Vídeo salvo: {dest_path} ({size_mb:.1f} MB)")
    return dest_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gera vídeo na nuvem e baixa para o PC (sem processamento local pesado)",
    )
    parser.add_argument(
        "--topic",
        required=True,
        help="Tema do vídeo (ex: 'A guerra dos emus na Austrália')",
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Modo produção completo (resumível, soundtrack, etc.)",
    )
    parser.add_argument(
        "--platform",
        default="youtube_dark",
        choices=["youtube_dark", "tiktok_shop"],
    )
    parser.add_argument(
        "--template",
        default=None,
        choices=["documentario", "dark5", "lofi_dark"],
        help="Template de roteiro (ex: lofi_dark para estilo Filosofatos)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_DOWNLOAD_DIR),
        help=f"Pasta local para salvar o MP4 (padrão: {DEFAULT_DOWNLOAD_DIR})",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Segundos entre consultas de status (padrão: 30)",
    )
    args = parser.parse_args()

    base_url = os.getenv("CLOUD_API_URL", "").strip()
    api_key = os.getenv("CLOUD_API_KEY", os.getenv("PIPELINE_API_KEY", "")).strip()

    if not base_url:
        print("❌ Configure CLOUD_API_URL no .env (ex: https://seu-app.up.railway.app)")
        print("   Guia: docs/deploy-railway.md")
        return 1
    if not api_key:
        print("❌ Configure CLOUD_API_KEY no .env (mesma PIPELINE_API_KEY do Railway)")
        print("   Atalho: .\\scripts\\cloud\\configurar_pc.ps1")
        return 1

    print(f"\n🎬 Gerando vídeo na nuvem: {args.topic}\n")
    if args.template:
        print(f"   Template: {args.template}\n")
    print(f"   Servidor: {base_url}\n")

    try:
        _check_health(base_url, api_key)
        job_id = _start_job(
            base_url,
            api_key,
            topic=args.topic,
            production=args.production,
            platform=args.platform,
            template=args.template,
        )
        result = _poll_status(
            base_url,
            api_key,
            job_id,
            interval=args.poll_interval,
        )
        output_path = result.get("output_path")
        if output_path:
            print(f"  Arquivo na nuvem: {output_path}")

        dest = _download_video(
            base_url,
            api_key,
            job_id,
            Path(args.output_dir),
        )
        print(f"\n✅ Pronto! Abra o vídeo: {dest}\n")
        return 0

    except requests.ConnectionError:
        print("❌ Não foi possível conectar ao servidor na nuvem.")
        print("   Verifique CLOUD_API_URL e se o deploy está Active no Railway.")
        print("   Guia: docs/deploy-railway.md")
        return 1
    except requests.Timeout:
        print("❌ Timeout ao contactar o servidor (provável 502 — app não responde na porta $PORT).")
        print("   Confira Deploy Logs no Railway e Settings → Networking → Target Port.")
        print("   Guia: docs/deploy-railway.md")
        return 1
    except Exception as exc:
        print(f"❌ Erro: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
