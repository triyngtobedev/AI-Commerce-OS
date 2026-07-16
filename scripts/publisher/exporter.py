import json
import shutil
import time

from pathlib import Path

from scripts.utils.slug import slugify


OUTPUT_DIR = Path("output")


def save_json(path, data):

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4
        )


def export_product(result):

    """
    Exporta todos os dados gerados pelo pipeline.

    Cada produto vira um pacote completo
    pronto para análise e publicação.
    """


    # =========================
    # NORMALIZAR RESULTADO
    # =========================

    if hasattr(result, "to_dict"):

        result = result.to_dict()


    if not isinstance(result, dict):

        raise TypeError(
            "Resultado do pipeline inválido."
        )


    produto = (
        result
        .get("produto", {})
        .get(
            "nome",
            "produto"
        )
    )


    folder = (
        OUTPUT_DIR
        /
        slugify(produto)
    )


    folder.mkdir(
        parents=True,
        exist_ok=True
    )


    conteudo = result.get(
        "conteudo",
        {}
    )


    if not isinstance(
        conteudo,
        dict
    ):

        conteudo = {}


    # =========================
    # COPIAR VÍDEO FINAL
    # =========================

    video_path = result.get(
        "video"
    )

    final_video = None


    if video_path:

        source = Path(video_path)


        if source.exists():

            destination = (
                folder
                /
                "video_final.mp4"
            )


            try:

                # Usa caminhos absolutos para comparação confiável
                # (evita armadilhas com paths relativos no Windows)
                source_path = source.resolve()
                dest_path = destination.resolve()

                if source_path == dest_path:

                    print(
                        "✅ Vídeo já está no destino correto. Pulando cópia."
                    )

                    final_video = str(dest_path)

                else:

                    copied = False

                    for attempt in range(5):

                        try:

                            shutil.copy2(
                                source_path,
                                dest_path
                            )

                            copied = True
                            break

                        except shutil.SameFileError:

                            # Fallback: SO detectou que é o mesmo arquivo
                            # mesmo com paths aparentemente diferentes
                            print(
                                "✅ Vídeo já está no destino "
                                "(detectado pelo SO). Pulando cópia."
                            )

                            copied = True
                            break

                        except PermissionError:

                            print(
                                "⚠️ Arquivo ocupado. Tentativa "
                                f"{attempt + 1}/5"
                            )

                            time.sleep(1)

                        except Exception as e:

                            print(
                                f"❌ Erro inesperado ao copiar vídeo: {e}"
                            )

                            # Usa o source como fallback para não perder o vídeo
                            final_video = str(source_path)
                            break

                    if copied:

                        final_video = str(dest_path)

                    else:

                        print(
                            "❌ Não foi possível copiar o vídeo após 5 tentativas."
                        )


            except Exception as error:

                print(
                    f"⚠️ Erro ao exportar vídeo: {error}"
                )


    # =========================
    # PACOTE TIKTOK
    # =========================

    hashtags = conteudo.get(
        "hashtags",
        []
    )


    if not isinstance(
        hashtags,
        list
    ):

        hashtags = [
            str(hashtags)
        ]


    post_package = {

        "produto":
            produto,

        "video":
            final_video,

        "titulo":
            conteudo.get(
                "titulo",
                produto
            ),

        "descricao":
            conteudo.get(
                "descricao",
                ""
            ),

        "hashtags":
            hashtags,

        "status":
            "READY_TO_POST"

    }


    files = {

        "analysis.json":
            result.get(
                "analise",
                {}
            ),

        "scenes.json":
            result.get(
                "cenas",
                {}
            ),

        "opportunity.json":
            result.get(
                "oportunidade",
                {}
            ),

        "decision.json":
            {
                "acao":
                    result.get(
                        "acao",
                        "avaliar"
                    )
            },

        "script.json":
            result.get(
                "roteiro",
                {}
            ),

        "strategy.json":
            result.get(
                "estrategia",
                {}
            ),

        "content.json":
            conteudo,

        "caption.json":
            result.get(
                "legenda",
                {}
            ),

        "asset_queries.json":
            result.get(
                "asset_queries",
                []
            ),

        "media.json":
            {
                "audio":
                    result.get(
                        "audio"
                    ),

                "subtitle_file":
                    result.get(
                        "subtitle_file"
                    ),

                "video":
                    final_video
            },

        "post_package.json":
            post_package

    }


    for filename, data in files.items():

        save_json(
            folder / filename,
            data
        )


    (folder / "roteiro.txt").write_text(

        json.dumps(
            result.get(
                "roteiro",
                {}
            ),
            ensure_ascii=False,
            indent=2
        ),

        encoding="utf-8"

    )


    (folder / "descricao.txt").write_text(

        str(
            conteudo.get(
                "descricao",
                ""
            )
        ),

        encoding="utf-8"

    )


    (folder / "narracao.txt").write_text(

        str(
            conteudo.get(
                "texto_narracao",
                ""
            )
        ),

        encoding="utf-8"

    )


    (folder / "hashtags.txt").write_text(

        "\n".join(
            hashtags
        ),

        encoding="utf-8"

    )


    print(
        "\n📦 EXPORTAÇÃO CONCLUÍDA"
    )


    print(
        f"Produto: {produto}"
    )


    print(
        f"Local: {folder}"
    )


    return folder