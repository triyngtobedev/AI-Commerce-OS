"""
Preparador de texto para TTS (Edge-TTS).

Otimiza pontuação, pausas e formatação para narração mais natural.
"""

import re

SECTION_PAUSE = " ... "
SENTENCE_PAUSE = ". "


def _normalize_numbers(text: str) -> str:
    """Converte números com separador de milhar para forma falada."""

    def _replace_thousands(match):
        num = match.group(0).replace(".", "")
        try:
            value = int(num)
            if value >= 1000:
                return _number_to_words_pt(value)
            return str(value)
        except ValueError:
            return match.group(0)

    text = re.sub(r"\b\d{1,3}(?:\.\d{3})+\b", _replace_thousands, text)

    return text


def _number_to_words_pt(n: int) -> str:
    """Converte inteiros comuns para palavras em português."""

    if n < 0:
        return f"menos {_number_to_words_pt(-n)}"

    units = [
        "", "um", "dois", "três", "quatro", "cinco",
        "seis", "sete", "oito", "nove", "dez",
        "onze", "doze", "treze", "quatorze", "quinze",
        "dezesseis", "dezessete", "dezoito", "dezenove",
    ]
    tens = [
        "", "", "vinte", "trinta", "quarenta", "cinquenta",
        "sessenta", "setenta", "oitenta", "noventa",
    ]

    if n < 20:
        return units[n]

    if n < 100:
        remainder = n % 10
        base = tens[n // 10]
        if remainder:
            return f"{base} e {units[remainder]}"
        return base

    if n < 1000:
        hundreds = n // 100
        remainder = n % 100
        if hundreds == 1:
            prefix = "cento" if remainder else "cem"
        else:
            prefix = f"{units[hundreds]}centos"
        if remainder:
            return f"{prefix} e {_number_to_words_pt(remainder)}"
        return prefix

    if n < 1_000_000:
        thousands = n // 1000
        remainder = n % 1000
        if thousands == 1:
            prefix = "mil"
        else:
            prefix = f"{_number_to_words_pt(thousands)} mil"
        if remainder:
            return f"{prefix} e {_number_to_words_pt(remainder)}"
        return prefix

    return str(n)


def _normalize_ranges(text: str) -> str:
    """Converte intervalos numéricos para forma falada."""

    def _replace_range(match):
        start = match.group(1)
        end = match.group(2)
        return f"de {start} a {end}"

    text = re.sub(
        r"\b(\d+)\s*[-–]\s*(\d+)\b",
        _replace_range,
        text,
    )

    return text


def _normalize_dates(text: str) -> str:
    """Melhora leitura de datas comuns."""

    months = {
        "01": "janeiro", "02": "fevereiro", "03": "março",
        "04": "abril", "05": "maio", "06": "junho",
        "07": "julho", "08": "agosto", "09": "setembro",
        "10": "outubro", "11": "novembro", "12": "dezembro",
    }

    def _replace_date(match):
        day = match.group(1)
        month = months.get(match.group(2), match.group(2))
        year = match.group(3)
        return f"{day} de {month} de {year}"

    text = re.sub(
        r"\b(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\b",
        _replace_date,
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\b(\d{1,2})/(\d{2})/(\d{4})\b",
        _replace_date,
        text,
    )

    return text


def _convert_pause_markers(text: str) -> str:
    """Converte [PAUSA] do roteiro em pausa longa para TTS."""

    return re.sub(r"\[PAUSA\]", " ... ... ", text, flags=re.IGNORECASE)


def _add_breathing_pauses(text: str) -> str:
    """Insere pausas naturais para ritmo documental e suspense."""

    text = re.sub(r"\.\s+Mas\s+", ". ... Mas ", text)
    text = re.sub(r"\.\s+E\s+é\s+aqui", ". ... E é aqui", text)
    text = re.sub(r"\.\s+No entanto,", ". ... No entanto,", text)
    text = re.sub(r"\.\s+Além disso,", ". ... Além disso,", text)
    text = re.sub(r"\?\s+", "? ... ", text)
    text = re.sub(r"!\s+", "! ... ", text)
    text = re.sub(r"\.\s+O que\s+", ". ... O que ", text)
    text = re.sub(r"\.\s+Ninguém\s+", ". ... Ninguém ", text)
    text = re.sub(r"\.\s+Até hoje", ". ... Até hoje", text)
    text = re.sub(r"\.\s+Mas o que", ". ... Mas o que", text)
    text = re.sub(r",\s+que\s+", ", ... que ", text, count=2)

    return text


def _clean_whitespace(text: str) -> str:
    """Normaliza espaços e pontuação duplicada."""

    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\.{4,}", "...", text)
    text = re.sub(r"\s+\.", ".", text)
    text = re.sub(r"\s+,", ",", text)

    return text.strip()


def prepare_text_for_tts(text: str) -> str:
    """
    Prepara texto de narração para síntese de voz natural.
    """

    if not text:
        return ""

    result = text
    result = _normalize_numbers(result)
    result = _normalize_ranges(result)
    result = _normalize_dates(result)
    result = _add_breathing_pauses(result)
    result = _clean_whitespace(result)
    result = _convert_pause_markers(result)

    return result
