from scripts.ai.router import ask_ai


def generate_content_ai(prompt):

    return ask_ai(
        prompt,
        task="content"
    )