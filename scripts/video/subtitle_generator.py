from pathlib import Path

from scripts.utils.slug import content_output_dir


def _output_folder(subject):
    platform = subject.get("_output_platform")
    return content_output_dir(subject, platform=platform)


def _format_srt_time(seconds) -> str:
    """Converte segundos (int ou float) para formato SRT HH:MM:SS,mmm."""

    try:
        total = float(seconds)
    except (TypeError, ValueError):
        total = 0.0

    if total < 0:
        total = 0.0

    hours = int(total // 3600)
    minutes = int((total % 3600) // 60)
    secs = int(total % 60)
    millis = int(round((total % 1) * 1000))

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _chunk_subtitle_text(text: str, max_chars: int = 80) -> list:
    """
    Divide texto longo em blocos legíveis para legenda.
    Prioriza quebras em pontuação.
    """

    text = text.strip()

    if not text or len(text) <= max_chars:
        return [text] if text else []

    sentences = []
    current = ""

    for part in text.replace("...", ".|").split(". "):
        part = part.replace(".|", "...").strip()

        if not part:
            continue

        candidate = f"{current} {part}".strip() if current else part

        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                sentences.append(current)
            current = part

    if current:
        sentences.append(current)

    return sentences or [text[:max_chars]]


def generate_subtitles(result):

    product = result["produto"]

    folder = _output_folder(product)

    folder.mkdir(parents=True, exist_ok=True)

    subtitle_file = folder / "captions.srt"

    cenas_data = result.get("cenas", {})

    if isinstance(cenas_data, dict):
        scenes = cenas_data.get("cenas", [])
    else:
        scenes = cenas_data

    if not scenes:
        texto = result.get("conteudo", {}).get("texto_narracao", "")

        if texto:
            scenes = [{"tempo": "0-30", "narracao": texto}]

    with open(subtitle_file, "w", encoding="utf-8") as file:
        index = 1

        for scene in scenes:
            inicio = scene.get("tempo_inicio")
            fim = scene.get("tempo_fim")

            if inicio is None or fim is None:
                tempo = scene.get("tempo", "0-5")
                try:
                    start, end = tempo.split("-")
                    inicio = float(start)
                    fim = float(end)
                except ValueError:
                    inicio, fim = 0.0, 5.0

            texto = scene.get("narracao", scene.get("texto", ""))

            if not texto:
                continue

            chunks = _chunk_subtitle_text(texto)
            duration = max(0.5, fim - inicio)
            chunk_duration = duration / len(chunks)
            current = float(inicio)

            for chunk in chunks:
                chunk_end = min(current + chunk_duration, fim)

                file.write(f"{index}\n")
                file.write(
                    f"{_format_srt_time(current)} --> "
                    f"{_format_srt_time(chunk_end)}\n"
                )
                file.write(f"{chunk}\n\n")

                index += 1
                current = chunk_end

    print(f"📝 Legenda criada: {subtitle_file.resolve()}")

    return subtitle_file.resolve()
