"""Utilities for checking and downloading Whisper models."""

from faster_whisper.utils import download_model


def is_model_cached(model_size: str) -> bool:
    """Check whether the given Whisper model is already downloaded locally."""
    try:
        download_model(model_size, local_files_only=True)
        return True
    except Exception:
        return False


def download_model_sync(model_size: str) -> str:
    """Download (or verify) a Whisper model and return its cached path."""
    return download_model(model_size)
