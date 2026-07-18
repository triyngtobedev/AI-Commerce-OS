"""
Wrapper que substitui (ou augmenta) a geração local de cenas,
delegando para o n8n quando a integração estiver ativa.

Controlado pela variável de ambiente USE_N8N_FOR_SCENES=true/false
Quando false: chama a função original sem nenhuma alteração de comportamento.
Quando true:  delega para o orquestrador n8n via scene_client + scene_waiter.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.n8n_integration.scene_client import request_scene_generation
from src.n8n_integration.scene_waiter import wait_for_scene


def use_n8n_for_scenes() -> bool:
    """True quando USE_N8N_FOR_SCENES está habilitado no ambiente."""
    return os.getenv("USE_N8N_FOR_SCENES", "false").strip().lower() in (
        "true",
        "1",
        "yes",
    )


async def _generate_scene_video_fallback_n8n(
    scene_description: str,
    scene_query: str,
    output_path: Path,
    *,
    platform: str = "youtube",
    scene_tipo: str = "",
    emotion: str = "",
    style: str = "dark, cinematic, dramatic lighting, documentary",
    scene: dict | None = None,
) -> dict | None:
    scene_id = str(uuid4())
    job_id = os.getenv("PIPELINE_JOB_ID", "local")
    prompt = scene_query.strip() or scene_description.strip()
    if not prompt:
        print("[n8n] Prompt vazio — fallback local ignorado")
        return None

    metadata: dict[str, Any] = {
        "platform": platform,
        "scene_tipo": scene_tipo,
        "emotion": emotion,
        "style": style,
        "output_path": str(output_path),
        "aspect_ratio": "16:9" if platform in ("youtube", "youtube_dark") else "9:16",
        "duration": 5,
    }
    if scene:
        metadata["scene"] = scene
        direction = scene.get("visual_direction")
        if direction:
            metadata["visual_direction"] = direction

    try:
        await request_scene_generation(prompt, scene_id, job_id, metadata)
        result = await wait_for_scene(scene_id, job_id)
    except Exception as error:
        print(f"[n8n] Orquestrador falhou ({error}) — fallback Python local")
        from scripts.pipeline.shared_media import _generate_scene_video_fallback_local

        return _generate_scene_video_fallback_local(
            scene_description,
            scene_query,
            output_path,
            platform=platform,
            scene_tipo=scene_tipo,
            emotion=emotion,
            style=style,
            scene=scene,
        )

    if result.get("status") == "failed" or not result.get("video_path"):
        print("[n8n] Cena falhou no n8n — fallback Python local (Kling Web incluído)")
        from scripts.pipeline.shared_media import _generate_scene_video_fallback_local

        return _generate_scene_video_fallback_local(
            scene_description,
            scene_query,
            output_path,
            platform=platform,
            scene_tipo=scene_tipo,
            emotion=emotion,
            style=style,
            scene=scene,
        )

    video_path = result.get("video_path")
    if not video_path or not Path(video_path).exists():
        print(f"[n8n] Cena {scene_id} concluída sem video_path válido")
        return None

    src = Path(video_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() != output_path.resolve():
        shutil.copy2(src, output_path)

    return {
        "local_path": str(output_path),
        "api_used": result.get("provider_used") or "n8n",
        "scene_id": scene_id,
        "job_id": job_id,
    }


def generate_scene_video_fallback(
    scene_description: str,
    scene_query: str,
    output_path: Path,
    *,
    platform: str = "youtube",
    scene_tipo: str = "",
    emotion: str = "",
    style: str = "dark, cinematic, dramatic lighting, documentary",
    scene: dict | None = None,
) -> dict | None:
    """
    Gera vídeo de cena via pipeline local ou orquestrador n8n.

    Mesma assinatura de scripts.pipeline.shared_media._generate_scene_video_fallback_local.
    """
    if not use_n8n_for_scenes():
        from scripts.pipeline.shared_media import _generate_scene_video_fallback_local

        return _generate_scene_video_fallback_local(
            scene_description,
            scene_query,
            output_path,
            platform=platform,
            scene_tipo=scene_tipo,
            emotion=emotion,
            style=style,
            scene=scene,
        )

    print(f"[n8n] delegando geração de cena: {scene_query[:72]}")
    return asyncio.run(
        _generate_scene_video_fallback_n8n(
            scene_description,
            scene_query,
            output_path,
            platform=platform,
            scene_tipo=scene_tipo,
            emotion=emotion,
            style=style,
            scene=scene,
        )
    )
