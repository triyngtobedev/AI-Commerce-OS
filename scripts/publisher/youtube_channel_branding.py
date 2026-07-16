"""

Atualização de branding do canal YouTube via API.



Suporta:

  - Descrição do canal (snippet.description)

  - Banner do canal (channelBanners.insert + brandingSettings.image)



Nota: a foto de perfil é vinculada à conta Google e não pode ser

alterada pela YouTube Data API — deve ser aplicada manualmente.

"""



import json

import logging

from dataclasses import dataclass, field

from pathlib import Path

from typing import Any, Dict, List, Optional



from scripts.core.brand_profile import (

    BRAND_ASSETS,

    YOUTUBE_DARK_CHANNEL_DESCRIPTION,

)

from scripts.publisher.youtube_auth import (

    build_google_credentials,

    validate_credentials,

)

from scripts.youtube.upload_image_prep import prepare_youtube_upload_image, prepare_brand_upload_assets



logger = logging.getLogger(__name__)



BANNER_MIN_WIDTH = 2048

BANNER_MIN_HEIGHT = 1152

BANNER_MAX_BYTES = 6 * 1024 * 1024



MIME_BY_SUFFIX = {

    ".png": "image/png",

    ".jpg": "image/jpeg",

    ".jpeg": "image/jpeg",

}





@dataclass

class ImageFileReport:

    """Metadados e validação de um arquivo de imagem."""



    path: Path

    exists: bool

    valid: bool

    absolute_path: str = ""

    file_name: str = ""

    size_bytes: int = 0

    width: int = 0

    height: int = 0

    format: str = ""

    color_mode: str = ""

    unique_colors_sampled: int = 0

    is_blank: bool = False

    messages: List[str] = field(default_factory=list)



    def log_lines(self) -> List[str]:

        lines = [

            f"  arquivo: {self.file_name}",

            f"  caminho absoluto: {self.absolute_path}",

            f"  tamanho: {self.size_bytes} bytes",

            f"  dimensões: {self.width}x{self.height}",

            f"  formato: {self.format or 'desconhecido'}",

            f"  modo de cor: {self.color_mode or 'desconhecido'}",

            f"  cores distintas (amostra): {self.unique_colors_sampled}",

            f"  pixels válidos: {'sim' if self.valid and not self.is_blank else 'não'}",

        ]

        lines.extend(f"  ⚠️ {message}" for message in self.messages)

        return lines





@dataclass

class ChannelBrandingResult:

    """Resultado da aplicação de branding no canal."""



    success: bool

    channel_id: Optional[str] = None

    channel_title: Optional[str] = None

    description_updated: bool = False

    banner_updated: bool = False

    profile_picture_note: str = ""

    messages: List[str] = field(default_factory=list)

    manual_steps: List[str] = field(default_factory=list)



    def summary(self) -> str:

        lines = ["=== Branding do Canal YouTube ==="]



        for message in self.messages:

            lines.append(message)



        if self.channel_title:

            lines.append(f"Canal: {self.channel_title} ({self.channel_id})")



        if self.manual_steps:

            lines.append("")

            lines.append("Passos manuais necessários:")

            for step in self.manual_steps:

                lines.append(f"  • {step}")



        return "\n".join(lines)





def _log_branding(stage: str, message: str, payload: Optional[Dict[str, Any]] = None):

    """Registra etapa de branding no logger e no console."""



    if payload:

        logger.info("[%s] %s — %s", stage, message, json.dumps(payload, ensure_ascii=False))

        print(f"[BRANDING:{stage}] {message}")

        print(json.dumps(payload, indent=2, ensure_ascii=False))

    else:

        logger.info("[%s] %s", stage, message)

        print(f"[BRANDING:{stage}] {message}")





def _validate_image_file(

    image_path: Path,

    *,

    min_width: int = 1,

    min_height: int = 1,

    max_bytes: Optional[int] = None,

    label: str = "imagem",

) -> ImageFileReport:

    """

    Valida arquivo de imagem com Pillow antes do upload.



    Confirma existência, metadados e presença de pixels não uniformes.

    """



    resolved = image_path.resolve()

    report = ImageFileReport(

        path=image_path,

        exists=resolved.exists(),

        valid=False,

        absolute_path=str(resolved),

        file_name=resolved.name,

    )



    if not report.exists:

        report.messages.append(f"{label} não encontrada: {resolved}")

        return report



    report.size_bytes = resolved.stat().st_size



    if report.size_bytes == 0:

        report.messages.append("arquivo vazio (0 bytes)")

        return report



    if max_bytes and report.size_bytes > max_bytes:

        report.messages.append(

            f"tamanho {report.size_bytes} bytes excede o limite de {max_bytes} bytes"

        )

        return report



    try:

        from PIL import Image

    except ImportError as error:

        report.messages.append(f"Pillow não instalado: {error}")

        return report



    try:

        with Image.open(resolved) as img:

            img.load()

            report.width, report.height = img.size

            report.format = img.format or resolved.suffix.lstrip(".").upper()

            report.color_mode = img.mode



            if report.width < min_width or report.height < min_height:

                report.messages.append(

                    f"dimensões {report.width}x{report.height} abaixo do mínimo "

                    f"{min_width}x{min_height}"

                )

                return report



            pixels = list(img.getdata())

            sample_size = min(len(pixels), 5000)

            sample = pixels[:sample_size]

            report.unique_colors_sampled = len(set(sample))



            if report.color_mode in ("RGB", "RGBA"):

                report.is_blank = report.unique_colors_sampled <= 1

                if report.is_blank:

                    report.messages.append(

                        "imagem contém apenas uma cor — provável arquivo corrompido ou vazio"

                    )

                    return report



                if all(

                    pixel[:3] == (255, 255, 255)

                    for pixel in sample

                    if isinstance(pixel, tuple)

                ):

                    report.messages.append(

                        "amostra de pixels é inteiramente branca — upload seria inválido"

                    )

                    return report



            report.valid = True

            return report



    except Exception as error:

        report.messages.append(f"falha ao abrir imagem: {error}")

        return report





def _append_image_report(

    messages: List[str],

    title: str,

    report: ImageFileReport,

) -> None:

    """Adiciona relatório de imagem à lista de mensagens do resultado."""



    status = "✅" if report.valid else "❌"

    messages.append(f"{status} {title}")

    messages.extend(report.log_lines())





def _build_media_upload(image_path: Path):

    """

    Prepara upload binário sem conversão intermediária.



    Usa caminho absoluto e MIME explícito para evitar envio incorreto

    do arquivo (causa comum de banner branco no YouTube).

    """



    from googleapiclient.http import MediaFileUpload



    resolved = image_path.resolve()

    suffix = resolved.suffix.lower()

    mimetype = MIME_BY_SUFFIX.get(suffix)



    if not mimetype:

        raise ValueError(

            f"Formato não suportado para upload: {suffix}. "

            f"Use: {', '.join(sorted(MIME_BY_SUFFIX))}"

        )



    return MediaFileUpload(

        str(resolved),

        mimetype=mimetype,

        resumable=False,

    )





def _get_youtube_service():

    """Constrói cliente YouTube Data API v3 autenticado."""



    from googleapiclient.discovery import build



    credentials = build_google_credentials()

    return build("youtube", "v3", credentials=credentials)





def _get_channel_id(youtube) -> dict:

    """Obtém ID e título do canal autenticado."""



    response = youtube.channels().list(

        part="snippet,brandingSettings",

        mine=True,

    ).execute()



    items = response.get("items", [])



    if not items:

        raise ValueError("Nenhum canal encontrado para esta conta")



    channel = items[0]

    return {

        "id": channel["id"],

        "title": channel["snippet"]["title"],

        "snippet": channel.get("snippet", {}),

        "branding": channel.get("brandingSettings", {}),

    }





def update_channel_description(

    description: str,

    youtube=None,

) -> bool:

    """Atualiza a descrição do canal."""



    if youtube is None:

        youtube = _get_youtube_service()



    channel = _get_channel_id(youtube)



    youtube.channels().update(

        part="snippet",

        body={

            "id": channel["id"],

            "snippet": {

                "title": channel["snippet"]["title"],

                "description": description,

            },

        },

    ).execute()



    return True





def update_channel_banner(

    banner_path: Path,

    youtube=None,

) -> Dict[str, Any]:

    """

    Faz upload e aplica banner do canal.



    Fluxo em duas etapas conforme documentação da API:

    1. channelBanners.insert — upload da imagem

    2. channels.update — aplica URL em brandingSettings.image

    """



    report = _validate_image_file(

        banner_path,

        min_width=BANNER_MIN_WIDTH,

        min_height=BANNER_MIN_HEIGHT,

        max_bytes=BANNER_MAX_BYTES,

        label="banner",

    )



    _log_branding(

        "VALIDACAO",

        "Arquivo validado antes do upload",

        {

            "absolute_path": report.absolute_path,

            "file_name": report.file_name,

            "size_bytes": report.size_bytes,

            "dimensions": f"{report.width}x{report.height}",

            "format": report.format,

            "color_mode": report.color_mode,

            "unique_colors_sampled": report.unique_colors_sampled,

            "valid": report.valid,

            "messages": report.messages,

        },

    )



    if not report.valid:

        raise ValueError(

            "Banner inválido para upload: " + "; ".join(report.messages)

        )



    if youtube is None:

        youtube = _get_youtube_service()



    channel = _get_channel_id(youtube)

    upload_path = prepare_youtube_upload_image(

        Path(report.absolute_path),

        max_bytes=BANNER_MAX_BYTES,

    )

    upload_report = _validate_image_file(

        upload_path,

        min_width=BANNER_MIN_WIDTH,

        min_height=BANNER_MIN_HEIGHT,

        max_bytes=BANNER_MAX_BYTES,

        label="banner (upload JPEG)",

    )

    _log_branding(

        "CONVERSAO",

        "Arquivo convertido para JPEG compatível com YouTube",

        {

            "source": report.absolute_path,

            "upload_path": str(upload_path.resolve()),

            "upload_size_bytes": upload_report.size_bytes,

            "upload_dimensions": f"{upload_report.width}x{upload_report.height}",

            "upload_valid": upload_report.valid,

        },

    )

    if not upload_report.valid:

        raise ValueError(

            "Banner convertido inválido: " + "; ".join(upload_report.messages)

        )

    media = _build_media_upload(upload_path)



    _log_branding(

        "UPLOAD",

        "Enviando banner via channelBanners.insert",

        {

            "channel_id": channel["id"],

            "media_mimetype": media.mimetype(),

            "media_size": media.size(),

            "source_file": report.absolute_path,

            "upload_file": str(upload_path.resolve()),

        },

    )



    banner_response = youtube.channelBanners().insert(

        channelId=channel["id"],

        media_body=media,

    ).execute()



    _log_branding("UPLOAD", "Resposta channelBanners.insert", banner_response)



    banner_url = banner_response.get("url")

    if not banner_url:

        raise ValueError(

            "API não retornou URL do banner: "

            + json.dumps(banner_response, ensure_ascii=False)

        )



    branding = channel.get("branding", {})

    existing_image = branding.get("image", {})

    branding_settings = {

        "image": {

            **existing_image,

            "bannerExternalUrl": banner_url,

        },

    }



    if "channel" in branding:

        branding_settings["channel"] = branding["channel"]



    update_body = {

        "id": channel["id"],

        "brandingSettings": branding_settings,

    }



    _log_branding(

        "APLICACAO",

        "Aplicando banner via channels.update",

        {

            "channel_id": channel["id"],

            "bannerExternalUrl": banner_url,

        },

    )



    update_response = youtube.channels().update(

        part="brandingSettings",

        body=update_body,

    ).execute()



    _log_branding("APLICACAO", "Resposta channels.update", update_response)



    applied_url = (

        update_response.get("brandingSettings", {})

        .get("image", {})

        .get("bannerExternalUrl")

    )



    if applied_url != banner_url:

        raise ValueError(

            "Canal não confirmou o banner aplicado. "

            f"esperado={banner_url} recebido={applied_url}"

        )



    return {

        "banner_insert_response": banner_response,

        "channel_update_response": update_response,

        "banner_url": banner_url,

        "image_report": report,

        "upload_file": str(upload_path.resolve()),

    }





def apply_channel_branding(

    description: Optional[str] = None,

    banner_path: Optional[Path] = None,

    profile_path: Optional[Path] = None,

    dry_run: bool = False,

) -> ChannelBrandingResult:

    """

    Aplica branding completo no canal YouTube.



    Args:

        description: Texto da descrição (padrão: YOUTUBE_DARK_CHANNEL_DESCRIPTION)

        banner_path: Caminho do banner PNG (padrão: assets/brand/banner.png)

        profile_path: Caminho da foto de perfil (apenas para referência manual)

        dry_run: Se True, apenas valida e reporta sem alterar o canal

    """



    description = description or YOUTUBE_DARK_CHANNEL_DESCRIPTION

    banner_path = Path(banner_path or (BRAND_ASSETS / "banner.png"))

    profile_path = Path(profile_path or (BRAND_ASSETS / "profile_picture.png"))

    upload_assets = prepare_brand_upload_assets(banner_path, profile_path)

    profile_upload = upload_assets["profile_upload"]



    result = ChannelBrandingResult(success=False)



    result.profile_picture_note = (

        "A foto de perfil é controlada pela conta Google e não pode ser "

        "alterada via YouTube Data API."

    )

    result.manual_steps.append(

        f"Foto de perfil: YouTube Studio → Personalização → "

        f"Fazer upload de {profile_upload.resolve()} "

        f"(JPEG preparado; original em {profile_path.resolve()})"

    )



    banner_report = _validate_image_file(

        banner_path,

        min_width=BANNER_MIN_WIDTH,

        min_height=BANNER_MIN_HEIGHT,

        max_bytes=BANNER_MAX_BYTES,

        label="banner",

    )

    profile_report = _validate_image_file(

        profile_path,

        min_width=1,

        min_height=1,

        label="foto de perfil",

    )



    status = validate_credentials(test_connection=not dry_run)



    if not status.configured:

        result.messages.append("❌ Credenciais YouTube não configuradas")

        result.messages.append(

            "   Execute: python main.py --youtube-auth"

        )

        return result



    if dry_run:

        result.messages.append("🔍 Modo dry-run — nenhuma alteração será feita")

        result.messages.append(f"✅ Descrição preparada ({len(description)} caracteres)")

        _append_image_report(result.messages, "Banner (pré-upload)", banner_report)

        _append_image_report(

            result.messages,

            "Foto de perfil (upload manual — não enviada pela API)",

            profile_report,

        )

        result.success = banner_report.valid and profile_report.valid

        return result



    if not status.valid:

        for message in status.messages:

            result.messages.append(message)

        return result



    result.channel_id = status.channel_id

    result.channel_title = status.channel_title



    _append_image_report(result.messages, "Banner validado antes do upload", banner_report)

    _append_image_report(

        result.messages,

        "Foto de perfil validada (referência para upload manual)",

        profile_report,

    )



    if not banner_report.valid:

        result.messages.append("❌ Banner inválido — upload cancelado")

        result.manual_steps.append(

            f"Banner: YouTube Studio → Personalização → "

            f"Fazer upload de {banner_path.resolve()}"

        )

        return result



    try:

        youtube = _get_youtube_service()



        update_channel_description(description, youtube=youtube)

        result.description_updated = True

        result.messages.append("✅ Descrição do canal atualizada")



        upload_result = update_channel_banner(banner_path, youtube=youtube)

        result.banner_updated = True

        result.messages.append("✅ Banner do canal atualizado")

        result.messages.append(

            f"   URL aplicada: {upload_result['banner_url']}"

        )



        result.success = result.description_updated and result.banner_updated



    except Exception as error:

        error_msg = str(error)

        logger.exception("Falha ao aplicar branding do canal")



        if "insufficient" in error_msg.lower() or "403" in error_msg:

            result.messages.append(

                "❌ Permissão insuficiente para atualizar branding do canal"

            )

            result.messages.append(

                "   Reautorize com escopo ampliado: python main.py --youtube-auth"

            )

            result.manual_steps.append(

                f"Descrição: copie o conteúdo de "

                f"{BRAND_ASSETS / 'channel_description.txt'}"

            )

            result.manual_steps.append(

                f"Banner: YouTube Studio → Personalização → "

                f"Fazer upload de {banner_path.resolve()}"

            )

        else:

            result.messages.append(f"❌ Erro: {error_msg}")



    return result


