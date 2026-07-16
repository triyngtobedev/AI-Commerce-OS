"""
Tipos estritos para Hugging Face Inference Providers (text-to-image via router).
"""

from __future__ import annotations

from typing import Callable, Literal, TypedDict

from scripts.video.media_providers.huggingface.errors import HFErrorCode

try:
    from typing import NotRequired, Required
except ImportError:  # pragma: no cover
    from typing_extensions import NotRequired, Required  # type: ignore[import-not-found]


MetricKind = Literal["image"]
ProviderName = Literal["fal-ai", "together"]


class HFImageSize(TypedDict):
    width: int
    height: int


class FalAIImageRequest(TypedDict):
    prompt: str
    image_size: HFImageSize
    num_inference_steps: int


class FalAIImageItem(TypedDict, total=False):
    url: Required[str]
    width: NotRequired[int]
    height: NotRequired[int]
    content_type: NotRequired[str]


class FalAIImageResponse(TypedDict):
    images: list[FalAIImageItem]


class TogetherImageDataItem(TypedDict):
    b64_json: str


class TogetherImageResponse(TypedDict):
    data: list[TogetherImageDataItem]


class HFHubProviderMapping(TypedDict, total=False):
    status: str
    providerId: str
    task: str
    isModelAuthor: bool


class HFHubModelInfo(TypedDict, total=False):
    inferenceProviderMapping: dict[str, HFHubProviderMapping]


class HFMetrics(TypedDict):
    kind: MetricKind
    success: bool
    error_code: HFErrorCode | None
    duration_ms: int
    attempts: int
    model_id: str
    provider: ProviderName | str


OnHFMetricsCallback = Callable[[HFMetrics], None]
