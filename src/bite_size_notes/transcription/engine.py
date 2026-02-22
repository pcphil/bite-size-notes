"""Whisper transcription engine using faster-whisper."""

import numpy as np
from faster_whisper import WhisperModel


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
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )

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
