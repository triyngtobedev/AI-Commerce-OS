"""
Retention Controller — converte retention_report em ações executáveis.

Limites de segurança:
- Máximo 3 ações por vídeo
- move_scene só entre cenas do mesmo ato
- cut_scene só se critical != true
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

from scripts.youtube.retention_analyzer import RetentionReport

MAX_ACTIONS = 3
CRITICAL_SCENE_TIPOS = frozenset({"hook", "revelacao", "encerramento"})

_ACT_RANGES = {
    1: {"hook", "contexto", "gancho", "abertura"},
    2: {
        "desenvolvimento", "desenvolvimento_1", "desenvolvimento_2",
        "demonstracao", "reflexao_1", "reflexao_2", "reflexao_3",
        "conexoes", "aprofundamento", "fato_5", "fato_4", "fato_3", "fato_2", "fato_1",
    },
    3: {"revelacao", "consequencias", "impacto", "encerramento", "beneficio", "resultado", "cta"},
}


def _scene_act(scene: dict) -> int:
    tipo = scene.get("tipo") or scene.get("scene_type") or ""
    for act, tipos in _ACT_RANGES.items():
        if tipo in tipos:
            return act
    index = scene.get("index", 0)
    if index <= 1:
        return 1
    if index <= 4:
        return 2
    return 3


def _is_critical(scene: dict) -> bool:
    if scene.get("critical") is True:
        return True
    tipo = scene.get("tipo") or scene.get("scene_type") or ""
    return tipo in CRITICAL_SCENE_TIPOS


def generate_retention_actions(
    report: RetentionReport | dict,
    scenes: dict,
    *,
    script: Optional[dict] = None,
) -> dict:
    """Gera retention_actions.json a partir do relatório de retenção."""

    if isinstance(report, RetentionReport):
        data = report.to_dict()
    else:
        data = report

    scene_list = scenes.get("cenas", [])
    actions: list[dict] = []

    if data.get("hook_strength", 100) < 60 and scene_list:
        revelacao_text = ""
        for scene in scene_list:
            if scene.get("tipo") == "revelacao":
                revelacao_text = (scene.get("narracao") or "")[:120]
                break
        hook_content = script.get("hook", "")[:80] if script else ""
        preview = revelacao_text or hook_content
        if preview:
            actions.append({
                "type": "inject_hook",
                "at": 0,
                "duration_s": 5,
                "content": f"Pergunta provocativa + preview: {preview[:100]}",
                "reason": "hook fraco nos primeiros 15s",
            })

    slow = data.get("slow_scenes") or []
    for slow_name in slow[:1]:
        for index, scene in enumerate(scene_list):
            if scene.get("tipo") == slow_name or slow_name in str(scene.get("tipo", "")):
                duration = float(scene.get("duration", 0) or 0)
                if duration > 18 and not _is_critical(scene):
                    actions.append({
                        "type": "shorten_scene",
                        "index": index,
                        "from_s": duration,
                        "to_s": max(10.0, duration * 0.55),
                        "reason": "cena lenta reduz retenção prevista",
                    })
                break

    if data.get("payoff_missing") and len(scene_list) > 4:
        revelacao_idx = next(
            (i for i, s in enumerate(scene_list) if s.get("tipo") == "revelacao"),
            None,
        )
        if revelacao_idx and revelacao_idx > 3:
            target = 2
            if _scene_act(scene_list[revelacao_idx]) == _scene_act(scene_list[target]):
                actions.append({
                    "type": "move_scene",
                    "from": revelacao_idx,
                    "to": target,
                    "reason": "revelação forte perdida no meio",
                })

    repetitions = data.get("repetitions") or []
    if repetitions and len(scene_list) > 6:
        for index, scene in enumerate(scene_list):
            if scene.get("tipo") in ("desenvolvimento_2", "consequencias"):
                if not _is_critical(scene):
                    actions.append({
                        "type": "cut_scene",
                        "index": index,
                        "reason": "tangente, quebra de ritmo previsto -18% retenção",
                    })
                    break

    return {"actions": actions[:MAX_ACTIONS]}


def _apply_move_scene(scene_list: list, action: dict) -> bool:
    src = action.get("from")
    dst = action.get("to")
    if src is None or dst is None or src == dst:
        return False
    if src >= len(scene_list) or dst >= len(scene_list):
        return False
    if _scene_act(scene_list[src]) != _scene_act(scene_list[dst]):
        return False

    item = scene_list.pop(src)
    scene_list.insert(dst, item)
    return True


def _apply_cut_scene(scene_list: list, action: dict) -> bool:
    index = action.get("index")
    if index is None or index >= len(scene_list):
        return False
    if _is_critical(scene_list[index]):
        return False
    scene_list.pop(index)
    return True


def _apply_shorten_scene(scene_list: list, action: dict) -> bool:
    index = action.get("index")
    if index is None or index >= len(scene_list):
        return False
    scene = scene_list[index]
    to_s = float(action.get("to_s", 12))
    scene["duration"] = to_s
    scene["retention_trimmed"] = True
    return True


def _apply_inject_hook(scenes: dict, action: dict) -> bool:
    hook_scene = {
        "tipo": "hook",
        "narracao": action.get("content", ""),
        "duration": float(action.get("duration_s", 5)),
        "injected_hook": True,
        "visual": "close-up dramatic tension documentary",
    }
    cenas = scenes.setdefault("cenas", [])
    cenas.insert(0, hook_scene)
    return True


def apply_retention_actions(
    scenes: dict,
    actions_payload: dict,
) -> tuple[dict, list[dict]]:
    """Aplica ações com limites de segurança. Retorna (scenes, log)."""

    updated = deepcopy(scenes)
    scene_list = updated.get("cenas", [])
    applied: list[dict] = []

    for action in (actions_payload.get("actions") or [])[:MAX_ACTIONS]:
        action_type = action.get("type")
        ok = False

        if action_type == "move_scene":
            ok = _apply_move_scene(scene_list, action)
        elif action_type == "cut_scene":
            ok = _apply_cut_scene(scene_list, action)
        elif action_type == "shorten_scene":
            ok = _apply_shorten_scene(scene_list, action)
        elif action_type == "inject_hook":
            ok = _apply_inject_hook(updated, action)
            scene_list = updated.get("cenas", [])

        entry = dict(action)
        entry["applied"] = ok
        applied.append(entry)

    for index, scene in enumerate(scene_list):
        scene["index"] = index

    updated["retention_actions_applied"] = applied
    return updated, applied


def run_retention_controller(
    scenes: dict,
    *,
    retention_report: RetentionReport | dict,
    script: Optional[dict] = None,
    output_dir: Optional[Path] = None,
) -> tuple[dict, dict]:
    """Gera retention_actions.json, aplica e retorna cenas atualizadas."""

    actions_payload = generate_retention_actions(
        retention_report,
        scenes,
        script=script,
    )

    if output_dir:
        path = Path(output_dir) / "retention_actions.json"
        path.write_text(
            json.dumps(actions_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    updated, applied = apply_retention_actions(scenes, actions_payload)

    if output_dir:
        log_path = Path(output_dir) / "retention_actions_log.json"
        log_path.write_text(
            json.dumps({"applied": applied}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return updated, actions_payload
