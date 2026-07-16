"""
Hierarquia de erros do provedor Hugging Face Serverless Inference API.
"""

from __future__ import annotations

from enum import Enum
from typing import Mapping


class HFErrorCode(str, Enum):
    CONFIG = "HF_CONFIG"
    AUTH = "HF_AUTH"
    RATE_LIMITED = "HF_RATE_LIMITED"
    MODEL_LOADING = "HF_MODEL_LOADING"
    CONNECTIVITY = "HF_CONNECTIVITY"
    TIMEOUT = "HF_TIMEOUT"
    QUALITY_THRESHOLD = "HF_QUALITY_THRESHOLD"
    SCHEMA_VALIDATION = "HF_SCHEMA_VALIDATION"


class HFError(RuntimeError):
    code: HFErrorCode
    details: Mapping[str, object]

    def __init__(
        self,
        code: HFErrorCode,
        message: str,
        *,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


class HFConfigError(HFError):
    def __init__(self, message: str, *, details: Mapping[str, object] | None = None) -> None:
        super().__init__(HFErrorCode.CONFIG, message, details=details)


class HFAuthError(HFError):
    def __init__(self, message: str, *, details: Mapping[str, object] | None = None) -> None:
        super().__init__(HFErrorCode.AUTH, message, details=details)


class HFRateLimitError(HFError):
    def __init__(self, message: str, *, details: Mapping[str, object] | None = None) -> None:
        super().__init__(HFErrorCode.RATE_LIMITED, message, details=details)


class HFModelLoadingError(HFError):
    def __init__(self, message: str, *, details: Mapping[str, object] | None = None) -> None:
        super().__init__(HFErrorCode.MODEL_LOADING, message, details=details)


class HFConnectivityError(HFError):
    def __init__(self, message: str, *, details: Mapping[str, object] | None = None) -> None:
        super().__init__(HFErrorCode.CONNECTIVITY, message, details=details)


class HFTimeoutError(HFError):
    def __init__(self, message: str, *, details: Mapping[str, object] | None = None) -> None:
        super().__init__(HFErrorCode.TIMEOUT, message, details=details)


class HFQualityError(HFError):
    def __init__(self, message: str, *, details: Mapping[str, object] | None = None) -> None:
        super().__init__(HFErrorCode.QUALITY_THRESHOLD, message, details=details)


class HFSchemaError(HFError):
    def __init__(self, message: str, *, details: Mapping[str, object] | None = None) -> None:
        super().__init__(HFErrorCode.SCHEMA_VALIDATION, message, details=details)
