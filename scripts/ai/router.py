import os

from dotenv import load_dotenv
from groq import Groq

from scripts.ai.providers.gemini import generate as gemini_generate

load_dotenv()

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


def ask_ai(prompt, context_type):
    # 1. Tenta Gemini (google.genai)
    try:
        return gemini_generate(prompt)
    except Exception:
        print(
            "⚠️ Gemini indisponível, tentando Groq..."
        )

    # 2. Tenta Groq
    try:
        completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.3-70b-versatile",
        )

        return completion.choices[0].message.content

    except Exception as error:
        print(
            f"❌ Falha total: {error}"
        )
        raise Exception(
            "Nenhuma API de IA disponível."
        )
