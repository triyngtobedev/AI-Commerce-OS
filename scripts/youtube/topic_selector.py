"""
Seleção de temas para pipeline YouTube Dark.

Evita reprocessar temas já gerados ou publicados,
mantendo o cache válido apenas para o mesmo tema.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from scripts.core.platform_config import YOUTUBE_DARK
from scripts.metrics.metrics_tracker import get_processed_subject_names
from scripts.utils.slug import slugify, content_output_dir
from scripts.youtube.topic_scorer import calculate_topic_score, rank_topics

PROCESSED_STATUSES = {
    "produced",
    "published",
    "produced_not_uploaded",
}

OUTPUT_MARKERS = (
    "youtube_package.json",
    "content.json",
    "video_final.mp4",
)


def _normalize_topic_name(name: str) -> str:
    return str(name or "").strip().casefold()


def _topic_slug(topic: Dict[str, Any], platform: str) -> str:
    return content_output_dir(
        topic,
        platform=platform,
    ).name


def _output_dir_has_artifacts(path: Path) -> bool:
    if not path.is_dir():
        return False

    for marker in OUTPUT_MARKERS:
        if (path / marker).exists():
            return True

    return False


def collect_processed_topic_names(
    platform: str = YOUTUBE_DARK.id,
    output_base: str = "output",
) -> Set[str]:
    """
    Retorna nomes normalizados de temas já gerados ou publicados.

    Fontes:
        - database/metrics.json (produções registradas)
        - pastas em output/<platform>/ com artefatos de vídeo
    """

    processed = {
        _normalize_topic_name(name)
        for name in get_processed_subject_names(platform)
    }

    platform_dir = Path(output_base) / platform

    if platform_dir.is_dir():
        for folder in platform_dir.iterdir():
            if not folder.is_dir():
                continue

            if not _output_dir_has_artifacts(folder):
                continue

            processed.add(folder.name)

    return processed


def is_topic_processed(
    topic: Dict[str, Any],
    processed_names: Optional[Set[str]] = None,
    platform: str = YOUTUBE_DARK.id,
    output_base: str = "output",
) -> bool:
    """Verifica se o tema já foi gerado ou publicado."""

    if processed_names is None:
        processed_names = collect_processed_topic_names(
            platform=platform,
            output_base=output_base,
        )

    normalized_name = _normalize_topic_name(
        topic.get("nome", "")
    )

    if normalized_name in processed_names:
        return True

    slug = _topic_slug(topic, platform)

    return slug in processed_names


def select_next_topics(
    topics: List[Dict[str, Any]],
    max_videos: int = 1,
    platform: str = YOUTUBE_DARK.id,
    output_base: str = "output",
    force_topic_name: Optional[str] = None,
    processed_names: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Seleciona próximos temas disponíveis por score, excluindo já processados.

    Args:
        topics: Temas carregados do banco
        max_videos: Quantidade máxima a produzir
        platform: Plataforma alvo
        output_base: Diretório base de saída
        force_topic_name: Tema específico (ignora exclusão de histórico)

    Returns:
        Lista de temas selecionados para produção
    """

    if not topics:
        return []

    if processed_names is None:
        processed_names = collect_processed_topic_names(
            platform=platform,
            output_base=output_base,
        )

    if force_topic_name:
        forced = _normalize_topic_name(force_topic_name)

        for topic in topics:
            if _normalize_topic_name(topic.get("nome", "")) == forced:
                print(
                    f"🎯 Tema forçado: {topic['nome']}"
                )
                return [topic]

        print(
            f"⚠️ Tema forçado não encontrado: {force_topic_name}"
        )

    available = []

    for topic in topics:
        if is_topic_processed(
            topic,
            processed_names=processed_names,
            platform=platform,
            output_base=output_base,
        ):
            print(
                f"⏭️ Tema já processado (ignorado): {topic['nome']}"
            )
            continue

        available.append(topic)

    if not available:
        print(
            "⚠️ Nenhum tema novo disponível — todos já foram processados."
        )
        return []

    scored = []

    for topic in available:
        topic["_output_platform"] = platform

        scored.append({
            "produto": topic,
            "score": calculate_topic_score(topic),
        })

    ranked = rank_topics(scored)

    selected = [
        item["produto"]
        for item in ranked[:max_videos]
    ]

    print(
        f"✅ {len(selected)} tema(s) novo(s) selecionado(s) "
        f"de {len(available)} disponível(is)"
    )

    return selected


def resolve_topic_for_production(
    topic: Dict[str, Any],
    all_topics: List[Dict[str, Any]],
    processed_names: Optional[Set[str]] = None,
    platform: str = YOUTUBE_DARK.id,
    output_base: str = "output",
) -> Optional[Dict[str, Any]]:
    """
    Valida o tema antes da produção e troca automaticamente
    por outro disponível quando o atual já foi processado.
    """

    if processed_names is None:
        processed_names = collect_processed_topic_names(
            platform=platform,
            output_base=output_base,
        )

    if not is_topic_processed(
        topic,
        processed_names=processed_names,
        platform=platform,
        output_base=output_base,
    ):
        return topic

    print(
        f"⚠️ Tema '{topic['nome']}' já processado — "
        f"buscando alternativa..."
    )

    alternatives = select_next_topics(
        all_topics,
        max_videos=1,
        platform=platform,
        output_base=output_base,
        processed_names=processed_names,
    )

    if not alternatives:
        print(
            f"❌ Nenhuma alternativa para '{topic['nome']}'."
        )
        return None

    replacement = alternatives[0]

    print(
        f"🔄 Tema substituído por: {replacement['nome']}"
    )

    return replacement
