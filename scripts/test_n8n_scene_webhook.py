#!/usr/bin/env python3
"""Testa webhook n8n de geração de cena (free tier Replicate → HF)."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"


def load_env() -> dict[str, str]:
    data: dict[str, str] = {}
    if not ENV.exists():
        return data
    for line in ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip()
    return data


def http_json(method: str, url: str, body: dict | None = None, headers: dict | None = None) -> dict:
    hdrs = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def main() -> int:
    env = load_env()
    api_key = env.get("PIPELINE_API_KEY", "")
    webhook_url = env.get(
        "N8N_SCENE_WEBHOOK_URL",
        "http://localhost:5678/webhook/scene-generation",
    )
    api_base = env.get("PIPELINE_API_BASE_URL", "http://127.0.0.1:8000")
    callback_base = env.get("N8N_CALLBACK_BASE_URL", api_base)

    if not api_key:
        print("PIPELINE_API_KEY ausente em .env", file=sys.stderr)
        return 1

    print("1) Criando job de pipeline...")
    job = http_json(
        "POST",
        f"{api_base.rstrip('/')}/api/v1/pipeline/run",
        {"platform": "youtube_dark", "production": False, "max_videos": 1},
        {"X-API-Key": api_key},
    )
    job_id = job["job_id"]
    print(f"   job_id={job_id}")

    scene_id = str(uuid.uuid4())
    prompt = (
        "historical documentary aerial shot, eastern front 1942, "
        "dark cinematic 16:9, atmospheric war footage"
    )
    callback_url = f"{callback_base.rstrip('/')}/api/v1/scenes/callback"

    print("2) Disparando webhook n8n (Replicate -> HF)...")
    print(f"   scene_id={scene_id}")
    print(f"   prompt={prompt[:72]}...")

    webhook_body = {
        "scene_id": scene_id,
        "job_id": job_id,
        "prompt": prompt,
        "metadata": {
            "aspect_ratio": "16:9",
            "platform": "youtube_dark",
            "scene_tipo": "contexto",
        },
        "callback_url": callback_url,
    }
    hdrs = {"Content-Type": "application/json"}
    secret = env.get("N8N_WEBHOOK_SECRET", "")
    if secret:
        hdrs["X-Webhook-Secret"] = secret

    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(webhook_body).encode("utf-8"),
        headers=hdrs,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"   webhook ack HTTP {resp.status}")
    except urllib.error.HTTPError as exc:
        print(f"   webhook erro HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}")
        return 1

    print("3) Aguardando callback (até 6 min)...")
    deadline = time.time() + 360
    while time.time() < deadline:
        status = http_json(
            "GET",
            f"{api_base.rstrip('/')}/api/v1/pipeline/status/{job_id}",
            headers={"X-API-Key": api_key},
        )
        scenes = status.get("scenes") or {}
        scene = scenes.get(scene_id)
        if scene:
            print(f"   status={scene.get('status')} provider={scene.get('provider_used')}")
            if scene.get("status") == "completed" and scene.get("video_path"):
                print(f"\nOK — video_path={scene['video_path']}")
                return 0
            if scene.get("status") == "failed":
                print(f"\nFALHOU — {scene.get('error_message')}")
                return 1
        time.sleep(10)

    print("\nTIMEOUT — verifique execução no n8n UI (Executions)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
