"""
Retry com backoff exponencial para APIs, downloads e uploads.
"""

from __future__ import annotations

import functools
import time
from typing import Callable, Optional, Tuple, Type, Any

from scripts.core.production.logger import get_logger


DEFAULT_RETRIABLE = (
    ConnectionError,
    TimeoutError,
    OSError,
)

try:
    import requests

    DEFAULT_RETRIABLE = DEFAULT_RETRIABLE + (requests.RequestException,)
except ImportError:
    requests = None  # type: ignore


def retry_with_backoff(
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retriable: Tuple[Type[BaseException], ...] = DEFAULT_RETRIABLE,
    operation: str = "operation",
):
    """
    Decorator que executa retry com backoff exponencial.

    Registra todas as tentativas nos logs de produção.
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger("retry")
            last_error: Optional[BaseException] = None

            for attempt in range(1, max_attempts + 1):
                try:
                    if attempt > 1:
                        logger.info(
                            f"Tentativa {attempt}/{max_attempts} — {operation}"
                        )
                    return func(*args, **kwargs)
                except retriable as exc:
                    last_error = exc
                    if attempt >= max_attempts:
                        logger.error(
                            f"Falha definitiva após {max_attempts} tentativas — {operation}",
                            error=str(exc),
                        )
                        raise

                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    logger.warning(
                        f"Tentativa {attempt}/{max_attempts} falhou — {operation}. "
                        f"Retry em {delay:.1f}s: {exc}"
                    )
                    time.sleep(delay)

            if last_error:
                raise last_error

            return func(*args, **kwargs)

        return wrapper

    return decorator


def requests_get_with_retry(url: str, **kwargs) -> Any:
    """GET HTTP com retry automático."""

    if requests is None:
        raise ImportError("requests não instalado")

    @retry_with_backoff(max_attempts=3, operation=f"GET {url[:60]}")
    def _get():
        response = requests.get(url, **kwargs)
        response.raise_for_status()
        return response

    return _get()
