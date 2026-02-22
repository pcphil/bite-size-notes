"""Audio mixing utilities."""

import numpy as np


def mix_audio(mic_audio: np.ndarray, loopback_audio: np.ndarray) -> np.ndarray:
    """Mix two mono audio signals, normalizing to prevent clipping."""
    max_len = max(len(mic_audio), len(loopback_audio))
    mic = np.pad(mic_audio, (0, max_len - len(mic_audio)))
    loop = np.pad(loopback_audio, (0, max_len - len(loopback_audio)))
    mixed = mic + loop
    peak = np.abs(mixed).max()
    if peak > 0:
        mixed = mixed / peak
    return mixed
