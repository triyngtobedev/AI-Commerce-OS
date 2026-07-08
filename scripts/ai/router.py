import os

from scripts.ai.providers import gemini
from scripts.ai.providers import mock
from scripts.ai.providers import openai


def ask_ai(prompt, task="analysis"):

    providers = {

        "analysis": "gemini",

        "script": "gemini",

        "content": "gemini"

    }

    provider = providers.get(
        task,
        "gemini"
    )


    mode = os.getenv(
        "GEMINI_MODE",
        "mock"
    )


    if mode == "live":

        if provider == "gemini":
            return gemini.generate(prompt)

        if provider == "openai":
            return openai.generate(prompt)


    return mock.generate(
        prompt,
        task
    )