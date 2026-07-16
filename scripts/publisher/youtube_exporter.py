"""
Exporter para YouTube.

Exporta pacote completo de publicação incluindo
metadados específicos do YouTube.
"""

import json
import shutil
import time
from pathlib import Path

from scripts.utils.slug import slugify, content_output_dir
from scripts.youtube.chapter_builder import (
    build_chapters,
    format_chapters_for_description,
)


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
            indent=4,
        )



def export_youtube_video(result):
    """
    Exporta pacote completo para publicação no YouTube.
    """

    if hasattr(result, "to_dict"):

        result = result.to_dict()


    if not isinstance(result, dict):

        raise TypeError(
            "Resultado do pipeline inválido."
        )


    platform = result.get(
        "platform",
        "youtube_dark"
    )


    produto = (
        result
        .get("produto", {})
        .get("nome", "video")
    )


    folder = content_output_dir(
        result.get("produto", {}),
        platform=platform,
    )


    folder.mkdir(
        parents=True,
        exist_ok=True,
    )


    conteudo = result.get("conteudo", {})

    if not isinstance(conteudo, dict):

        conteudo = {}


    youtube_meta = result.get(
        "youtube_metadata",
        {}
    )


    # Copiar vídeo final
    video_path = result.get("video")
    final_video = None


    if video_path:

        source = Path(video_path)


        if source.exists():

            destination = folder / "video_final.mp4"

            try:

                source_path = source.resolve()
                dest_path = destination.resolve()

                if source_path != dest_path:

                    for attempt in range(5):

                        try:

                            shutil.copy2(
                                source_path,
                                dest_path,
                            )

                            break

                        except PermissionError:

                            time.sleep(1)


                final_video = str(dest_path)

            except Exception as error:

                print(
                    f"⚠️ Erro ao exportar vídeo: {error}"
                )


    # Capítulos
    chapters = build_chapters(
        conteudo,
        result.get("cenas"),
    )


    chapter_block = format_chapters_for_description(
        chapters
    )


    descricao = conteudo.get("descricao", "")

    if chapter_block and chapter_block not in descricao:

        descricao += chapter_block


    tags = conteudo.get("tags", [])

    if not isinstance(tags, list):

        tags = [str(tags)]


    post_package = {
        "platform": "youtube",
        "produto": produto,
        "video": final_video,
        "thumbnail": youtube_meta.get("thumbnail"),
        "titulo": conteudo.get("titulo", produto),
        "titulo_alternativos": conteudo.get(
            "titulo_alternativos",
            []
        ),
        "descricao": descricao,
        "tags": tags,
        "capitulos": chapters,
        "categoria": conteudo.get(
            "categoria_youtube",
            "Education"
        ),
        "idioma": conteudo.get("idioma", "pt-BR"),
        "default_language": conteudo.get("idioma", "pt-BR"),
        "status": "READY_TO_UPLOAD",
    }


    files = {
        "analysis.json": result.get("analise", {}),
        "scenes.json": result.get("cenas", {}),
        "opportunity.json": result.get("oportunidade", {}),
        "decision.json": {
            "acao": result.get("acao", "avaliar"),
        },
        "script.json": result.get("roteiro", {}),
        "strategy.json": result.get("estrategia", {}),
        "content.json": conteudo,
        "caption.json": result.get("legenda", {}),
        "asset_queries.json": result.get(
            "asset_queries",
            []
        ),
        "chapters.json": chapters,
        "tags.json": {"tags": tags},
        "media.json": {
            "audio": result.get("audio"),
            "subtitle_file": result.get("subtitle_file"),
            "video": final_video,
            "thumbnail": youtube_meta.get("thumbnail"),
        },
        "post_package.json": post_package,
        "youtube_package.json": post_package,
    }


    for filename, data in files.items():

        save_json(
            folder / filename,
            data,
        )


    # Arquivos texto legíveis
    (folder / "roteiro.txt").write_text(
        json.dumps(
            result.get("roteiro", {}),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


    (folder / "descricao.txt").write_text(
        descricao,
        encoding="utf-8",
    )


    (folder / "narracao.txt").write_text(
        str(conteudo.get("texto_narracao", "")),
        encoding="utf-8",
    )


    (folder / "tags.txt").write_text(
        "\n".join(tags),
        encoding="utf-8",
    )


    if chapters:

        chapter_text = format_chapters_for_description(
            chapters
        )

        (folder / "capitulos.txt").write_text(
            chapter_text,
            encoding="utf-8",
        )


    print(
        "\n📦 EXPORTAÇÃO YOUTUBE CONCLUÍDA"
    )

    print(
        f"Tema: {produto}"
    )

    print(
        f"Local: {folder}"
    )


    return folder
