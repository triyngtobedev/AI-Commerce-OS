from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

PROMPTS_DIR = BASE_DIR / "prompts"


def load_prompt(name):
    prompt_path = PROMPTS_DIR / f"{name}.md"

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt não encontrado: {prompt_path}"
        )

    return prompt_path.read_text(encoding="utf-8")