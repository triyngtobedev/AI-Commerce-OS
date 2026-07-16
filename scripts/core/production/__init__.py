"""
Infraestrutura de produção contínua do AI-Commerce-OS.

Módulos:
  - logger: logging padronizado por etapa
  - retry: retry com backoff exponencial
  - hash_utils: hashes de arquivos e conteúdo
  - stage_cache: cache inteligente por etapa
  - pipeline_state: estado resumível do pipeline
  - health_check: validação pré-upload
  - manifest: production_manifest.json
  - performance_audit: relatório de performance
  - monetization_audit: detecção de repetição de conteúdo
  - resumable_pipeline: orquestrador resumível YouTube
"""

from scripts.core.production.logger import ProductionLogger, get_logger
from scripts.core.production.pipeline_state import PipelineState, PIPELINE_VERSION
from scripts.core.production.resumable_pipeline import run_resumable_youtube_pipeline

__all__ = [
    "ProductionLogger",
    "get_logger",
    "PipelineState",
    "PIPELINE_VERSION",
    "run_resumable_youtube_pipeline",
]
