from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

PROMPTS_DIR = BASE_DIR / "prompts"


def load_prompt(name, platform=None):
    """
    Carrega prompt por nome.

    Quando platform é informada, tenta primeiro o prompt
    específico da plataforma (ex: youtube_content_generation.md)
    e faz fallback para o prompt genérico.
    """

    if platform:
        platform_path = PROMPTS_DIR / f"{platform}_{name}.md"

        if platform_path.exists():
            return platform_path.read_text(encoding="utf-8")

    prompt_path = PROMPTS_DIR / f"{name}.md"

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt não encontrado: {prompt_path}"
        )

    return prompt_path.read_text(encoding="utf-8")