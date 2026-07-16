"""
YouTube Uploader

Publica vídeos automaticamente no YouTube via Data API v3.
Requer credenciais OAuth2 configuradas no .env.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from scripts.metrics.metrics_tracker import _load_metrics
from scripts.publisher.youtube_auth import (
    build_google_credentials,
    validate_credentials,
)

UPLOAD_STATUS = {
    "pending": "PENDING",
    "uploaded": "UPLOADED",
    "failed": "FAILED",
    "skipped": "SKIPPED",
}


def _log(step: str, message: str):
    """Log padronizado das etapas de upload."""

    print(f"[YouTube Upload] {step}: {message}")



def _published_titles() -> set:
    """Títulos já publicados no canal (via metrics)."""

    titles = set()

    for record in _load_metrics():
        if record.get("status") != "published":
            continue

        title = record.get("titulo")

        if title:
            titles.add(title.strip().lower())

    return titles



def _resolve_publish_title(package: Dict[str, Any]) -> str:
    """
    Garante título dinâmico do pipeline e evita duplicata no canal.
    """

    candidates = [package.get("titulo", "")]
    candidates.extend(package.get("titulo_alternativos", []))

    published = _published_titles()

    for candidate in candidates:
        title = str(candidate or "").strip()

        if not title:
            continue

        if title.lower() not in published:
            return title

    base = str(package.get("titulo") or package.get("produto") or "Vídeo").strip()
    suffix = 2

    while f"{base} ({suffix})".lower() in published:
        suffix += 1

    return f"{base} ({suffix})"


def _upload_error_message(status) -> str:
    """Mensagem orientativa quando upload não está configurado."""

    lines = [
        "Credenciais YouTube não configuradas ou inválidas.",
    ]

    for message in status.messages:
        lines.append(f"   {message}")

    lines.append("")
    lines.append(
        "   Configure com: python main.py --youtube-auth"
    )
    lines.append(
        "   Ou valide com: python main.py --youtube-validate"
    )

    return "\n".join(lines)


def upload_video(
    package: Dict[str, Any],
    privacy_status: str = "private",
) -> Dict[str, Any]:
    """
    Faz upload de vídeo para o YouTube.

    Args:
        package: post_package.json ou youtube_package.json
        privacy_status: private | unlisted | public

    Returns:
        Dict com status, video_id e url (se sucesso)
    """

    _log("INÍCIO", "Iniciando upload para o YouTube")

    title = _resolve_publish_title(package)
    package["titulo"] = title
    _log("METADADOS", f"Título: {title}")
    _log("METADADOS", f"Privacidade: {privacy_status}")

    _log("CREDENCIAIS", "Validando credenciais OAuth...")
    status = validate_credentials(test_connection=True)

    for message in status.messages:
        _log("CREDENCIAIS", message)

    if not status.configured:
        error_msg = _upload_error_message(status)
        _log("CREDENCIAIS", "FALHA — credenciais incompletas")
        print(error_msg)

        return {
            "status": UPLOAD_STATUS["pending"],
            "message": "Credenciais não configuradas",
            "missing": status.missing,
        }

    if not status.valid:
        _log(
            "CREDENCIAIS",
            "FALHA — credenciais inválidas ou conexão falhou",
        )

        return {
            "status": UPLOAD_STATUS["failed"],
            "message": "Credenciais inválidas",
            "auth_error": True,
        }

    if status.channel_title:
        _log(
            "CREDENCIAIS",
            f"OK — canal: {status.channel_title} "
            f"({status.channel_id})",
        )

    video_path = package.get("video")

    if not video_path or not Path(video_path).exists():
        _log(
            "ARQUIVO",
            f"FALHA — vídeo não encontrado: {video_path}",
        )

        return {
            "status": UPLOAD_STATUS["failed"],
            "message": "Arquivo de vídeo não encontrado",
        }

    video_size_mb = round(
        Path(video_path).stat().st_size / (1024 * 1024),
        2,
    )
    _log("ARQUIVO", f"OK — {video_path} ({video_size_mb} MB)")

    thumbnail_path = package.get("thumbnail")
    if thumbnail_path and Path(thumbnail_path).exists():
        _log("ARQUIVO", f"Thumbnail: {thumbnail_path}")
    else:
        _log(
            "ARQUIVO",
            f"❌ ERRO: thumbnail ausente ou inválida "
            f"(package.thumbnail={thumbnail_path!r}) — "
            f"upload continuará sem capa customizada",
        )

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

    except ImportError:
        _log(
            "DEPENDÊNCIAS",
            "FALHA — google-api-python-client não instalado",
        )

        return {
            "status": UPLOAD_STATUS["pending"],
            "message": "Dependências de upload não instaladas",
        }

    try:
        _log("TOKEN", "Renovando access token via refresh token...")
        creds = build_google_credentials()
        _log("TOKEN", "OK — access token obtido")

        _log("API", "Conectando à YouTube Data API v3...")
        youtube = build(
            "youtube",
            "v3",
            credentials=creds,
        )
        _log("API", "OK — cliente YouTube inicializado")

        body = {
            "snippet": {
                "title": package.get("titulo", "Vídeo"),
                "description": package.get("descricao", ""),
                "tags": package.get("tags", []),
                "categoryId": _resolve_category_id(
                    package.get("categoria", "Education")
                ),
                "defaultLanguage": package.get(
                    "default_language",
                    package.get("idioma", "pt-BR"),
                ),
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        _log("ENVIO", "Iniciando upload resumable do vídeo...")

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None

        while response is None:
            status_chunk, response = request.next_chunk()

            if status_chunk:
                progress = int(status_chunk.progress() * 100)
                _log("ENVIO", f"Progresso: {progress}%")

        video_id = response.get("id")
        _log("RESPOSTA", f"Upload concluído — Video ID: {video_id}")

        if response.get("snippet"):
            _log(
                "RESPOSTA",
                f"Título confirmado: "
                f"{response['snippet'].get('title', title)}",
            )

        if video_id and thumbnail_path and Path(thumbnail_path).exists():
            _upload_thumbnail(youtube, video_id, thumbnail_path)
        elif video_id:
            _log(
                "THUMBNAIL",
                "❌ Pulando upload de thumbnail — arquivo não disponível no pacote",
            )

        video_url = f"https://youtube.com/watch?v={video_id}"

        result = {
            "status": UPLOAD_STATUS["uploaded"],
            "video_id": video_id,
            "url": video_url,
            "privacy_status": privacy_status,
            "channel_id": status.channel_id,
            "channel_title": status.channel_title,
        }

        _log("SUCESSO", f"Vídeo publicado: {video_url}")
        print(f"✅ Vídeo publicado: {video_url}")

        return result

    except ValueError as error:
        _log("ERRO", f"Autenticação: {error}")
        print(f"❌ Erro de autenticação: {error}")

        return {
            "status": UPLOAD_STATUS["failed"],
            "message": str(error),
            "auth_error": True,
        }

    except Exception as error:
        _log("ERRO", f"Upload: {error}")
        print(f"❌ Erro no upload: {error}")

        return {
            "status": UPLOAD_STATUS["failed"],
            "message": str(error),
        }


def _resolve_category_id(category: str) -> str:
    """Mapeia nome de categoria para ID do YouTube."""

    categories = {
        "Education": "27",
        "Entertainment": "24",
        "Science & Technology": "28",
        "News & Politics": "25",
        "People & Blogs": "22",
    }

    return categories.get(category, "27")


def _upload_thumbnail(
    youtube,
    video_id: str,
    thumbnail_path: str,
):
    """Faz upload da thumbnail customizada."""

    try:
        from googleapiclient.http import MediaFileUpload

        if not Path(thumbnail_path).exists():
            _log("THUMBNAIL", "Arquivo não encontrado — ignorado")
            return

        _log("THUMBNAIL", f"Enviando: {thumbnail_path}")

        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(
                thumbnail_path,
                mimetype="image/jpeg",
            ),
        ).execute()

        _log("THUMBNAIL", "OK — thumbnail enviada")
        print("🖼️ Thumbnail enviada.")

    except Exception as error:
        _log("THUMBNAIL", f"FALHA — {error}")
        print(f"⚠️ Erro ao enviar thumbnail: {error}")


def upload_from_folder(
    folder: Path,
    privacy_status: str = "private",
) -> Dict[str, Any]:
    """
    Carrega youtube_package.json e faz upload.
    """

    _log("PACOTE", f"Lendo pacote em: {folder}")

    package_file = folder / "youtube_package.json"

    if not package_file.exists():
        package_file = folder / "post_package.json"

    if not package_file.exists():
        _log(
            "PACOTE",
            "FALHA — youtube_package.json não encontrado",
        )

        return {
            "status": UPLOAD_STATUS["failed"],
            "message": "Pacote de publicação não encontrado",
        }

    _log("PACOTE", f"OK — {package_file.name}")

    with open(
        package_file,
        "r",
        encoding="utf-8",
    ) as file:
        package = json.load(file)

    return upload_video(
        package,
        privacy_status=privacy_status,
    )
