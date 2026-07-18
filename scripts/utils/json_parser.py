import json
import re


def _strip_markdown_fences(response: str) -> str:
    text = response.replace("```json", "").replace("```", "")
    return text.strip()


def _extract_json_object(text: str) -> str | None:
    """Extrai o primeiro objeto JSON balanceado de texto misto."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for index, char in enumerate(text[start:], start):
        if escape:
            escape = False
            continue
        if char == "\\" and in_string:
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return None


def parse_json(response):
    """
    Converte resposta JSON da IA em dicionário Python.

    Raises:
        json.JSONDecodeError: Se nenhuma estratégia de parse funcionar.
        ValueError: Se a resposta estiver vazia.
    """
    parsed = safe_parse_json(response)
    if parsed is None:
        raise ValueError("Resposta vazia ou JSON inválido")
    return parsed


def safe_parse_json(response) -> dict | list | None:
    """Como parse_json, mas retorna None em vez de levantar exceção."""
    if response is None:
        return None

    text = _strip_markdown_fences(str(response))
    if not text:
        return None

    candidates = [text]
    extracted = _extract_json_object(text)
    if extracted and extracted != text:
        candidates.append(extracted)

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    return None
