"""
AI-Commerce-OS

Entrada principal do sistema.
Executa pipeline completo:
Produto -> IA -> Roteiro -> Mídia -> Vídeo
"""

from scripts.pipeline.product_pipeline import run_pipeline


def run():

    print(
        "\n🚀 Iniciando AI-Commerce-OS\n"
    )

    results = run_pipeline()


    print(
        "\n=============================="
    )

    print(
        "PROCESSO FINALIZADO"
    )

    print(
        f"Vídeos gerados: {len(results)}"
    )

    print(
        "==============================\n"
    )


if __name__ == "__main__":
    run()