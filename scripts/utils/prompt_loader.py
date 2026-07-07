from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def load_prompt(filename):
    """
    Carrega um prompt da pasta prompts.
    """

    prompt_path = ROOT_DIR / "prompts" / filename

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt não encontrado: {prompt_path}"
        )

    return prompt_path.read_text(
        encoding="utf-8"
    )