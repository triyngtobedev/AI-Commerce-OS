from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class PipelineResult:
    """
    Estrutura padrão de dados que percorre o AI-Commerce-OS.

    Todo produto processado pelo pipeline deve seguir esse modelo.
    """

    produto: Dict[str, Any]

    analise: Dict[str, Any] = field(default_factory=dict)

    oportunidade: Dict[str, Any] = field(default_factory=dict)

    acao: str = "avaliar"

    roteiro: Dict[str, Any] = field(default_factory=dict)

    conteudo: Dict[str, Any] = field(default_factory=dict)

    legenda: Dict[str, Any] = field(default_factory=dict)

    cenas: Dict[str, Any] = field(default_factory=dict)

    asset_queries: list = field(default_factory=list)

    audio: Optional[str] = None

    subtitle_file: Optional[str] = None

    video: Optional[str] = None


    def to_dict(self):
        """
        Converte o objeto para o formato antigo
        usado pelos módulos existentes.
        """

        return {
            "produto": self.produto,

            "analise": self.analise,

            "oportunidade": self.oportunidade,

            "acao": self.acao,

            "roteiro": self.roteiro,

            "conteudo": self.conteudo,

            "legenda": self.legenda,

            "cenas": self.cenas,

            "asset_queries": self.asset_queries,

            "audio": self.audio,

            "subtitle_file": self.subtitle_file,

            "video": self.video,
        }