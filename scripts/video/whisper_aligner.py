"""
Whisper Aligner — timestamps reais de legenda a partir do áudio final.

Transcreve a narração renderizada (narracao.mp3) com faster-whisper, que roda
100% local e gratuito. Devolve palavras com start/end reais para que as
legendas sigam a fala em vez de uma estimativa por contagem de palavras.

Dependência OPCIONAL: se faster-whisper não estiver instalado (ou a
transcrição falhar), as funções retornam vazio e o Subtitle Engine mantém o
comportamento estimado atual. Nenhuma API paga é utilizada.
"""

from __future__ import annotations

import os
from pathlib import Path

# Modelos: tiny/base/small/medium. "small" equilibra precisão e custo em CPU.
_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "pt")
# Cache directory for Whisper models — Railway usa /tmp/whisper_cache (efêmero mas
# persiste durante o ciclo de vida do container, evitando redownload em todo request).
_MODEL_CACHE_DIR = os.getenv("WHISPER_CACHE_DIR", "").strip() or None

_model = None


def whisper_is_available() -> bool:
    """True quando faster-whisper pode ser importado."""

    try:
        import faster_whisper  # noqa: F401

        return True
    except Exception:
        return False


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        kwargs = {"device": "cpu", "compute_type": "int8"}
        if _MODEL_CACHE_DIR:
            kwargs["download_root"] = _MODEL_CACHE_DIR
        _model = WhisperModel(_MODEL_SIZE, **kwargs)
    return _model


def transcribe_words(audio_path, language: str | None = None) -> list[dict]:
    """
    Transcreve o áudio e retorna palavras com timestamps reais.

    Retorna lista de {"start": float, "end": float, "word": str}.
    Retorna [] quando indisponível ou em qualquer falha (fallback seguro).
    """

    from scripts.video.subtitle_generator import subtitles_enabled

    if not subtitles_enabled():
        return []

    path = Path(audio_path)
    if not path.exists() or not whisper_is_available():
        return []

    try:
        model = _get_model()
        segments, _info = model.transcribe(
            str(path.resolve()),
            language=language or _LANGUAGE,
            word_timestamps=True,
            vad_filter=True,
        )

        words: list[dict] = []
        for segment in segments:
            for word in (segment.words or []):
                text = (word.word or "").strip()
                if not text or word.start is None or word.end is None:
                    continue
                words.append({
                    "start": float(word.start),
                    "end": float(word.end),
                    "word": text,
                })

        return words

    except Exception as error:
        print(f"  ⚠️ Whisper indisponível/falhou ({error}); usando timing estimado.")
        return []
    finally:
        # Libera o modelo da memória e limpa cache se for Railway (disco limitado)
        _cleanup_whisper_cache()


def _cleanup_whisper_cache() -> None:
    """Remove cache do Whisper para liberar disco em ambientes com espaço limitado."""
    global _model
    if _model is not None:
        try:
            _model = None
            import gc
            gc.collect()
        except Exception:
            pass
