from scripts.ai.router import ask_ai


def generate_analysis(prompt):

    return ask_ai(
        prompt,
        task="analysis"
    )