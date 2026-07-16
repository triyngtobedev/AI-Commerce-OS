from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional



@dataclass
class PipelineResult:
    """
    Modelo central de dados do AI-Commerce-OS.

    Todo produto processado pelo sistema
    deve passar por essa estrutura.

    Fluxo:

    Produto
        ↓
    Análise
        ↓
    Oportunidade
        ↓
    Decisão
        ↓
    Roteiro
        ↓
    Conteúdo
        ↓
    Assets
        ↓
    Vídeo
    """


    produto: Dict[str, Any]


    analise: Dict[str, Any] = field(
        default_factory=dict
    )


    oportunidade: Dict[str, Any] = field(
        default_factory=dict
    )


    acao: str = "avaliar"


    estrategia: Dict[str, Any] = field(
        default_factory=dict
    )


    roteiro: Dict[str, Any] = field(
        default_factory=dict
    )


    conteudo: Dict[str, Any] = field(
        default_factory=dict
    )


    legenda: Dict[str, Any] = field(
        default_factory=dict
    )


    cenas: Dict[str, Any] = field(
        default_factory=dict
    )


    asset_queries: list = field(
        default_factory=list
    )


    audio: Optional[str] = None


    subtitle_file: Optional[str] = None


    video: Optional[str] = None


    platform: str = "tiktok_shop"


    youtube_metadata: Dict[str, Any] = field(
        default_factory=dict
    )


    def update(self, **kwargs):
        """
        Atualiza campos existentes do resultado.
        """

        for key, value in kwargs.items():

            if hasattr(
                self,
                key
            ):

                setattr(
                    self,
                    key,
                    value
                )

        return self



    def to_dict(self):
        """
        Converte para formato compatível
        com os módulos antigos.
        """

        return asdict(
            self
        )



    @classmethod
    def from_dict(
        cls,
        data: dict
    ):
        """
        Reconstrói um PipelineResult
        salvo anteriormente.
        """

        return cls(

            produto=data.get(
                "produto",
                {}
            ),

            analise=data.get(
                "analise",
                {}
            ),

            oportunidade=data.get(
                "oportunidade",
                {}
            ),

            acao=data.get(
                "acao",
                "avaliar"
            ),

            estrategia=data.get(
                "estrategia",
                {}
            ),

            roteiro=data.get(
                "roteiro",
                {}
            ),

            conteudo=data.get(
                "conteudo",
                {}
            ),

            legenda=data.get(
                "legenda",
                {}
            ),

            cenas=data.get(
                "cenas",
                {}
            ),

            asset_queries=data.get(
                "asset_queries",
                []
            ),

            audio=data.get(
                "audio"
            ),

            subtitle_file=data.get(
                "subtitle_file"
            ),

            video=data.get(
                "video"
            ),

            platform=data.get(
                "platform",
                "tiktok_shop"
            ),

            youtube_metadata=data.get(
                "youtube_metadata",
                {}
            )
        )



    def validate(self):
        """
        Verifica se o resultado possui
        dados mínimos para continuar.
        """

        errors = []


        if not self.produto:

            errors.append(
                "Produto ausente"
            )


        if not isinstance(
            self.produto,
            dict
        ):

            errors.append(
                "Produto deve ser um dicionário"
            )


        narracao = self.conteudo.get(
            "texto_narracao"
        )

        if not narracao:

            errors.append(
                "Narração ausente"
            )

        else:

            from scripts.youtube.narration_utils import (
                count_words,
                validate_narration,
                MIN_NARRATION_WORDS,
            )

            words = count_words(narracao)

            if words < MIN_NARRATION_WORDS // 2:

                errors.append(
                    f"Narração muito curta: {words} palavras "
                    f"(mínimo crítico: {MIN_NARRATION_WORDS // 2})"
                )

            for warning in validate_narration(narracao):
                print(f"⚠️ Validação: {warning}")


        cenas = self.cenas

        if isinstance(
            cenas,
            dict
        ):

            cenas = cenas.get(
                "cenas",
                []
            )


        if not cenas:

            errors.append(
                "Cenas ausentes"
            )


        return errors