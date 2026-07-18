"""
Chapter Builder para YouTube.

Constrói capítulos no formato aceito pelo YouTube
a partir das cenas ou do conteúdo gerado.
"""

from typing import Any, Dict, List


def _seconds_to_timestamp(seconds: int) -> str:
    """Converte segundos para formato HH:MM:SS ou MM:SS."""

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:

        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    return f"{minutes:02d}:{secs:02d}"



def _parse_time_range(tempo: str, scene: dict = None) -> int:
    """Extrai segundo inicial de cena sincronizada ou range legado."""

    if scene and scene.get("tempo_inicio") is not None:
        return int(float(scene["tempo_inicio"]))

    if not tempo:
        return 0

    start = tempo.split("-")[0].strip()

    try:
        return int(float(start))
    except ValueError:
        return 0



CHAPTER_LABELS = {
    "hook": "Introdução",
    "contexto": "Contexto Histórico",
    "desenvolvimento_1": "A História",
    "desenvolvimento_2": "Desenvolvimento",
    "revelacao": "A Revelação",
    "consequencias": "Consequências",
    "impacto": "Impacto Atual",
    "encerramento": "Conclusão",
    "abertura": "Abertura",
    "reflexao_1": "Reflexão I",
    "reflexao_2": "Reflexão II",
    "reflexao_3": "Reflexão III",
    "conexoes": "Conexões",
    "aprofundamento": "Aprofundamento",
    "demonstracao": "Demonstração",
    "beneficio": "Benefícios",
    "cta": "Conclusão",
}



def build_chapters_from_scenes(
    scenes: Dict[str, Any],
) -> List[Dict[str, str]]:
    """
    Gera capítulos a partir das cenas do vídeo.
    """

    cenas = scenes.get("cenas", [])

    if not cenas:

        return []


    chapters = []

    for cena in cenas:

        tempo = cena.get("tempo", "0-0")
        tipo = cena.get("tipo", "")

        start_seconds = _parse_time_range(tempo, cena)

        titulo = CHAPTER_LABELS.get(
            tipo,
            tipo.replace("_", " ").title()
        )


        chapters.append({
            "tempo": _seconds_to_timestamp(start_seconds),
            "titulo": titulo,
        })


    return chapters



def build_chapters(
    content: Dict[str, Any],
    scenes: Dict[str, Any] = None,
) -> List[Dict[str, str]]:
    """
    Retorna capítulos com timestamps reais quando cenas estão sincronizadas.
    """

    if scenes and isinstance(scenes, dict) and scenes.get("synced"):
        return build_chapters_from_scenes(scenes)

    capitulos = content.get("capitulos", [])

    if capitulos:
        return capitulos

    if scenes:
        return build_chapters_from_scenes(scenes)

    return []



def format_chapters_for_description(
    chapters: List[Dict[str, str]],
) -> str:
    """
    Formata capítulos para inclusão na descrição do YouTube.

    Formato:
        00:00 Introdução
        01:30 Contexto Histórico
    """

    if not chapters:

        return ""


    lines = ["\n📌 Capítulos:"]

    for chapter in chapters:

        tempo = chapter.get("tempo", "00:00")
        titulo = chapter.get("titulo", "")

        lines.append(
            f"{tempo} {titulo}"
        )


    return "\n".join(lines)
