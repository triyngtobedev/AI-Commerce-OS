"""
Retention Analyzer — análise e melhoria automática do roteiro antes da renderização.

Gera retention_report.json e reescreve trechos fracos quando possível.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Optional

# ask_ai importado lazy em improve_script_retention para evitar init de clientes sem API key


@dataclass
class RetentionReport:
    hook_strength: float = 0.0
    curiosity_gaps: int = 0
    pattern_interrupts: int = 0
    slow_scenes: list[str] = field(default_factory=list)
    repetitions: list[str] = field(default_factory=list)
    abstraction_excess: bool = False
    conflict_lacking: bool = False
    payoff_missing: bool = False
    overall_score: float = 0.0
    improvements_applied: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


_HOOK_PATTERNS = (
    r"\?",
    r"\d+",
    r"nunca|ninguém|segredo|impossível|milhões|bilhões",
    r"como|por que|porque",
)

_PATTERN_INTERRUPT_MARKERS = (
    "mas espere",
    "e aqui",
    "o pior",
    "não para por aí",
    "e isso não é",
    "até que",
    "de repente",
    "só que",
)


def _word_count(text: str) -> int:
    return len(text.split())


def _score_hook(hook_text: str) -> float:
    if not hook_text:
        return 0.0

    score = 40.0
    words = hook_text.split()
    if len(words) <= 80:
        score += 15
    if len(words) <= 50:
        score += 10

    hook_lower = hook_text.lower()
    for pattern in _HOOK_PATTERNS:
        if re.search(pattern, hook_lower):
            score += 8

    if "[PAUSA]" in hook_text:
        score += 5

    return min(100.0, score)


def _count_curiosity_gaps(script: dict) -> int:
    text = " ".join(str(v) for v in script.values() if isinstance(v, str))
    markers = ("mas ", "porém ", "só que ", "até que ", "ninguém sabia", "mistério")
    return sum(text.lower().count(m) for m in markers)


def _count_pattern_interrupts(script: dict) -> int:
    text = " ".join(str(v) for v in script.values() if isinstance(v, str)).lower()
    return sum(1 for m in _PATTERN_INTERRUPT_MARKERS if m in text)


def _find_repetitions(script: dict) -> list[str]:
    sentences = []
    for section in script.values():
        if isinstance(section, str):
            sentences.extend(re.split(r"[.!?]+", section))

    seen: dict[str, int] = {}
    repeated = []
    for sent in sentences:
        normalized = " ".join(sent.lower().split())
        if len(normalized) < 20:
            continue
        seen[normalized] = seen.get(normalized, 0) + 1
        if seen[normalized] == 2:
            repeated.append(normalized[:80])

    return repeated[:5]


def _detect_abstraction_excess(script: dict) -> bool:
    abstract_words = (
        "essencialmente", "fundamentalmente", "conceitualmente",
        "paradigma", "ecossistema", "sinergia", "holístico",
    )
    text = " ".join(str(v) for v in script.values() if isinstance(v, str)).lower()
    count = sum(text.count(w) for w in abstract_words)
    return count >= 4


def analyze_retention(script: dict) -> RetentionReport:
    """Analisa retenção do roteiro sem chamar IA."""

    hook = script.get("hook", "")
    report = RetentionReport(
        hook_strength=_score_hook(hook),
        curiosity_gaps=_count_curiosity_gaps(script),
        pattern_interrupts=_count_pattern_interrupts(script),
        repetitions=_find_repetitions(script),
        abstraction_excess=_detect_abstraction_excess(script),
    )

    dev = script.get("desenvolvimento", "")
    if isinstance(dev, str) and _word_count(dev) > 600 and report.pattern_interrupts < 3:
        report.slow_scenes.append("desenvolvimento")

    revelacao = script.get("revelacao", "")
    if isinstance(revelacao, str) and len(revelacao.split()) < 100:
        report.payoff_missing = True

    conflito_markers = ("mas ", "crise", "problema", "conflito", "batalha", "guerra", "disputa")
    full_text = " ".join(str(v) for v in script.values() if isinstance(v, str)).lower()
    report.conflict_lacking = sum(full_text.count(m) for m in conflito_markers) < 3

    # Score composto
    score = report.hook_strength * 0.30
    score += min(30, report.curiosity_gaps * 3)
    score += min(20, report.pattern_interrupts * 5)
    score -= len(report.repetitions) * 4
    score -= 10 if report.abstraction_excess else 0
    score -= 15 if report.conflict_lacking else 0
    score -= 15 if report.payoff_missing else 0

    report.overall_score = max(0.0, min(100.0, score))

    if report.hook_strength < 60:
        report.recommendations.append("Fortalecer hook nos primeiros 15 segundos")
    if report.pattern_interrupts < 3:
        report.recommendations.append("Adicionar pattern interrupts a cada 60-90 segundos")
    if report.conflict_lacking:
        report.recommendations.append("Introduzir mais tensão/conflito narrativo")
    if report.payoff_missing:
        report.recommendations.append("Expandir revelação/payoff")
    if report.repetitions:
        report.recommendations.append("Remover frases repetidas")

    return report


def improve_script_retention(
    script: dict,
    report: RetentionReport,
    *,
    topic: str = "",
) -> dict:
    """Reescreve trechos fracos via IA quando score abaixo do threshold."""

    if report.overall_score >= 70:
        return script

    weak_sections = []
    if report.hook_strength < 60:
        weak_sections.append("hook")
    if report.payoff_missing:
        weak_sections.append("revelacao")
    if "desenvolvimento" in report.slow_scenes:
        weak_sections.append("desenvolvimento")

    if not weak_sections:
        return script

    prompt = f"""Reescreva APENAS estas seções do roteiro documentário sobre "{topic}".
Mantenha tom dark documental, frases curtas (máx 12 palavras), pattern interrupts.

Seções a melhorar: {", ".join(weak_sections)}
Recomendações: {"; ".join(report.recommendations[:3])}

Roteiro atual (JSON):
{json.dumps({k: script.get(k, "") for k in weak_sections}, ensure_ascii=False)}

Retorne APENAS JSON com as seções reescritas."""

    try:
        from scripts.ai.router import ask_ai
        from scripts.utils.json_parser import safe_parse_json

        response = ask_ai(prompt, context_type="script")
        improved = safe_parse_json(response)
        if isinstance(improved, dict):
            updated = dict(script)
            for key, value in improved.items():
                if key in weak_sections and isinstance(value, str):
                    updated[key] = value
                    report.improvements_applied.append(key)
            return updated
    except Exception:
        pass

    return script


def run_retention_pipeline(
    script: dict,
    *,
    topic: str = "",
    output_dir: Optional[Path] = None,
    min_score: float = 65.0,
) -> tuple[dict, RetentionReport]:
    """Analisa, melhora e exporta retention_report.json."""

    report = analyze_retention(script)

    if report.overall_score < min_score:
        script = improve_script_retention(script, report, topic=topic)
        report = analyze_retention(script)
        report.improvements_applied = report.improvements_applied or []

    if output_dir:
        path = Path(output_dir) / "retention_report.json"
        path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    return script, report
