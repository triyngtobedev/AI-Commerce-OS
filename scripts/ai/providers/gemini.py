from scripts.ai.router import ask_ai


def generate(prompt, model="gemini-2.0-flash"):
    del model
    return ask_ai(prompt, "default")
