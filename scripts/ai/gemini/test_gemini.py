from client import ask_gemini


def main():

    resposta = ask_gemini(
        "Responda apenas: AI-Commerce-OS conectado com sucesso."
    )

    print(resposta)


if __name__ == "__main__":
    main()