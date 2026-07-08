from scripts.ai.router import ask_ai


def generate_script(prompt):

    return ask_ai(
        prompt,
        task="script"
    )