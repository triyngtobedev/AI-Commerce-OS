"""
T2V Decision Engine — uso seletivo de Text-to-Video (máx. 2 cenas/vídeo).

T2V só quando stock e fallback editorial não bastam e a cena agrega valor real.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional

MAX_T2V_SCENES = 2

# Tipos onde T2V raramente agrega valor
_T2V_AVOID_TYPES = {"data", "timeline", "map", "quote", "evidence", "resolution", "context"}

# Tipos onde T2V pode fazer sentido se stock falhar
_T2V_PREFERRED_TYPES = {"hook", "turning_point", "climax", "conflict", "character"}


@dataclass
class T2VDecision:
    should_use_t2v: bool
    reason: str
    prompt: str = ""
    negative_prompt: str = ""
    fallback_if_bad: str = "editorial_ken_burns"
    priority: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


_NEGATIVE_DEFAULT = (
    "cartoon, anime, fantasy, watermark, text overlay, logo, "
    "low quality, blurry, distorted, unrealistic, CGI look, "
    "slideshow, static image, meme, tiktok style"
)


def _build_t2v_prompt(scene: dict, query_item: dict) -> str:
    visual = scene.get("must_show") or scene.get("visual") or query_item.get("busca", "")
    tipo = scene.get("scene_type") or scene.get("tipo", "")
    emotion = scene.get("emotion", "calm")

    suffix = {
        "hook": "dramatic cinematic establishing shot, documentary film grain",
        "turning_point": "dramatic reveal moment, documentary realism",
        "climax": "intense documentary b-roll, real world footage style",
        "conflict": "tension documentary footage, handheld camera feel",
    }.get(tipo, "documentary cinematic footage, photorealistic, 16:9")

    return f"{visual}, {suffix}, {emotion} mood, no text, no watermark".strip(", ")


class T2VTracker:
    """Rastreia uso de T2V por vídeo."""

    def __init__(self, max_scenes: int = MAX_T2V_SCENES):
        self.max_scenes = max_scenes
        self.used_scenes: list[int] = []
        self.decisions: dict[int, T2VDecision] = {}

    @property
    def remaining(self) -> int:
        return max(0, self.max_scenes - len(self.used_scenes))

    def can_use_t2v(self) -> bool:
        return self.remaining > 0

    def record_use(self, scene_num: int, decision: T2VDecision) -> None:
        if scene_num not in self.used_scenes:
            self.used_scenes.append(scene_num)
        self.decisions[scene_num] = decision

    def to_dict(self) -> dict:
        return {
            "max_t2v_scenes": self.max_scenes,
            "used_count": len(self.used_scenes),
            "used_scene_ids": self.used_scenes,
            "remaining": self.remaining,
            "decisions": {str(k): v.to_dict() for k, v in self.decisions.items()},
        }


def evaluate_t2v_decision(
    scene_num: int,
    scene: dict,
    query_item: dict,
    *,
    tracker: T2VTracker,
    stock_failed: bool = True,
    editorial_failed: bool = False,
    scene_importance: float = 0.5,
) -> T2VDecision:
    """
    Decide se T2V deve ser usado para a cena.

    Critérios:
    - Stock e fallback editorial falharam (ou cena muito importante)
    - Limite de 2 T2V não excedido
    - Tipo de cena beneficia movimento gerado
    - Não parece solução padrão
    """

    editorial_type = scene.get("scene_type") or query_item.get("tipo", "")
    thumbnail_potential = scene.get("thumbnail_potential", False)
    visual_intent = scene.get("visual_intent", "")

    prompt = _build_t2v_prompt(scene, query_item)
    fallback = scene.get("fallback_visual_plan") or query_item.get("fallback_visual_plan") or "editorial_ken_burns"

    if not tracker.can_use_t2v():
        return T2VDecision(
            should_use_t2v=False,
            reason=f"T2V limit reached ({tracker.max_scenes} scenes max)",
            prompt=prompt,
            negative_prompt=_NEGATIVE_DEFAULT,
            fallback_if_bad=fallback,
        )

    if not stock_failed and not editorial_failed:
        return T2VDecision(
            should_use_t2v=False,
            reason="Stock or editorial fallback available — T2V not needed",
            prompt=prompt,
            negative_prompt=_NEGATIVE_DEFAULT,
            fallback_if_bad=fallback,
        )

    if editorial_type in _T2V_AVOID_TYPES and not editorial_failed:
        return T2VDecision(
            should_use_t2v=False,
            reason=f"Scene type '{editorial_type}' better served by motion graphics",
            prompt=prompt,
            negative_prompt=_NEGATIVE_DEFAULT,
            fallback_if_bad=fallback,
        )

    priority = 0
    if editorial_type in _T2V_PREFERRED_TYPES:
        priority += 3
    if thumbnail_potential:
        priority += 2
    if scene.get("tipo") in ("hook", "revelacao"):
        priority += 2
    if scene_importance > 0.7:
        priority += 1
    if visual_intent in ("cinematic_broll", "dramatic_reveal"):
        priority += 1

    # T2V precisa de prioridade mínima — nunca é default
    if priority < 2 and not editorial_failed:
        return T2VDecision(
            should_use_t2v=False,
            reason="Scene priority too low for T2V — use editorial fallback",
            prompt=prompt,
            negative_prompt=_NEGATIVE_DEFAULT,
            fallback_if_bad=fallback,
            priority=priority,
        )

    return T2VDecision(
        should_use_t2v=True,
        reason=f"T2V approved: stock failed, priority={priority}, type={editorial_type}",
        prompt=prompt,
        negative_prompt=_NEGATIVE_DEFAULT,
        fallback_if_bad=fallback,
        priority=priority,
    )
