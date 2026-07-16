"""
Director Engine — camada superior de direção do vídeo.

Responsável por decisões globais: ritmo, clímax, silêncios dramáticos,
distribuição de intensidade e encerramento. Módulos downstream apenas executam.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional

from scripts.creative.script_parser import enrich_script_with_emotions, parse_script_sections

CLIMAX_SECTIONS = {"revelacao", "impacto", "resultado"}
REVEAL_SECTIONS = {"revelacao", "desenvolvimento_2"}
CLOSING_SECTIONS = {"encerramento", "cta"}


@dataclass
class DirectorDecision:
    """Decisões globais de direção aplicadas a todo o vídeo."""

    rhythm: str = "moderate"
    climax_section: str = "revelacao"
    silence_moments: list[str] = None
    intensity_curve: list[float] = None
    reveal_timing: float = 0.65
    closing_style: str = "reflective"
    pacing_multiplier: float = 1.0

    def __post_init__(self):
        if self.silence_moments is None:
            self.silence_moments = []
        if self.intensity_curve is None:
            self.intensity_curve = []

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _detect_climax(sections: list[dict]) -> str:
    for section in sections:
        key = section.get("section_key", "")
        if key in CLIMAX_SECTIONS:
            return key
    if sections:
        mid = len(sections) // 2
        return sections[mid].get("section_key", "revelacao")
    return "revelacao"


def _build_intensity_curve(sections: list[dict], climax_key: str) -> list[float]:
    """Curva de intensidade: sobe até o clímax e desce no encerramento."""

    if not sections:
        return []

    climax_index = next(
        (i for i, s in enumerate(sections) if s.get("section_key") == climax_key),
        len(sections) // 2,
    )
    curve = []

    for index, section in enumerate(sections):
        base = float(section.get("intensity", 0.5))
        key = section.get("section_key", "")

        if key in CLOSING_SECTIONS:
            adjusted = max(0.2, base * 0.7)
        elif index <= climax_index:
            progress = index / max(1, climax_index)
            adjusted = min(1.0, base + progress * 0.25)
        else:
            progress = (index - climax_index) / max(1, len(sections) - climax_index - 1)
            adjusted = max(0.3, base - progress * 0.15)

        curve.append(round(adjusted, 2))

    return curve


def _resolve_rhythm(strategy: Optional[dict]) -> str:
    if not strategy:
        return "moderate"

    angulo = strategy.get("angulo", "")
    slow_angles = {"misterio_nao_resolvido", "cronologia_epica", "revelacao_historica"}
    fast_angles = {"fato_surpreendente", "impacto_historico"}

    if angulo in slow_angles:
        return "slow"
    if angulo in fast_angles:
        return "fast"
    return "moderate"


def _apply_directorial_pauses(
    sections: list[dict],
    decision: DirectorDecision,
) -> list[dict]:
    """Ajusta pausas dramáticas conforme decisões do diretor."""

    enriched = []
    for index, section in enumerate(sections):
        item = dict(section)
        key = item.get("section_key", "")

        pause_before = float(item.get("pause_before", 0.0))
        pause_after = float(item.get("pause_after", 0.0))

        if key in decision.silence_moments or key == decision.climax_section:
            pause_before = max(pause_before, 0.5)

        if key in REVEAL_SECTIONS:
            pause_before = max(pause_before, 0.3)
            pause_after = max(pause_after, 0.5)

        if key in CLOSING_SECTIONS:
            pause_after = max(pause_after, 0.4)

        if decision.rhythm == "slow":
            pause_after = max(pause_after, 0.3)
        elif decision.rhythm == "fast" and key not in CLIMAX_SECTIONS:
            pause_after = min(pause_after, 0.2)

        item["pause_before"] = round(pause_before, 2)
        item["pause_after"] = round(pause_after, 2)

        if decision.intensity_curve and index < len(decision.intensity_curve):
            item["intensity"] = decision.intensity_curve[index]

        enriched.append(item)

    return enriched


def direct_script(
    script: dict,
    strategy: Optional[dict] = None,
) -> tuple[dict, DirectorDecision]:
    """
    Aplica direção global ao roteiro.

    Retorna (script_enriquecido, DirectorDecision).
    """

    parsed = parse_script_sections(script)
    sections = parsed.get("sections", [])

    climax = _detect_climax(sections)
    rhythm = _resolve_rhythm(strategy)

    silence_moments = []
    for section in sections:
        key = section.get("section_key", "")
        if key in REVEAL_SECTIONS or key == climax:
            silence_moments.append(key)

    reveal_index = next(
        (i for i, s in enumerate(sections) if s.get("section_key") in REVEAL_SECTIONS),
        len(sections) // 2,
    )
    reveal_timing = round(reveal_index / max(1, len(sections) - 1), 2)

    closing_style = "reflective"
    if strategy and strategy.get("angulo") == "impacto_historico":
        closing_style = "powerful"
    elif strategy and strategy.get("angulo") == "misterio_nao_resolvido":
        closing_style = "open_ended"

    decision = DirectorDecision(
        rhythm=rhythm,
        climax_section=climax,
        silence_moments=silence_moments,
        reveal_timing=reveal_timing,
        closing_style=closing_style,
        pacing_multiplier=0.9 if rhythm == "slow" else 1.1 if rhythm == "fast" else 1.0,
    )
    decision.intensity_curve = _build_intensity_curve(sections, climax)

    directed_sections = _apply_directorial_pauses(sections, decision)

    enriched = enrich_script_with_emotions(script)
    enriched["sections"] = directed_sections
    enriched["_director"] = decision.to_dict()
    enriched["_script_format"] = parsed.get("format", "emotional")

    return enriched, decision


def get_director_decision(script: dict) -> Optional[DirectorDecision]:
    """Recupera decisões de direção já aplicadas ao roteiro."""

    meta = script.get("_director")
    if not meta:
        return None
    return DirectorDecision(**meta)
