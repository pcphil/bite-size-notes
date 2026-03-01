"""Whisper transcription engine using faster-whisper."""

import logging

import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class TranscriptionEngine:
    """Wraps faster-whisper for audio-to-text conversion."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "en",
    ):
        self.language = language
        logger.info("Loading Whisper model '%s' (device=%s)", model_size, device)
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )
        logger.info("Whisper model '%s' loaded", model_size)

    def transcribe(self, audio: np.ndarray) -> list[dict]:
        """Transcribe a numpy audio array (float32, 16kHz, mono).

        Returns list of segments: [{"start": float, "end": float, "text": str}]
        """
        segments, _info = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        results = []
        for seg in segments:
            text = seg.text.strip()
            if text:
                results.append(
                    {
                        "start": seg.start,
                        "end": seg.end,
                        "text": text,
                    }
                )
        return results
