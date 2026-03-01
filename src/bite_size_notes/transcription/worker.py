"""Transcription worker thread using Qt signals."""

import logging
import queue

from PySide6.QtCore import QThread, Signal

from bite_size_notes.transcription.engine import TranscriptionEngine

logger = logging.getLogger(__name__)


class TranscriberWorker(QThread):
    """Pulls audio chunks from the queue and runs Whisper transcription.

    Emits results via Qt signals for the GUI to consume.
    """

    # (source: str, timestamp: float, text: str)
    transcription_ready = Signal(str, float, str)
    model_loaded = Signal()
    error_occurred = Signal(str)

    def __init__(
        self,
        audio_queue: queue.Queue,
        model_size: str = "base",
        language: str = "en",
        engine: TranscriptionEngine | None = None,
    ):
        super().__init__()
        self.audio_queue = audio_queue
        self.model_size = model_size
        self.language = language
        self._engine = engine
        self._stop = False

    def run(self):
        logger.info("Transcriber worker starting")
        if self._engine is not None:
            engine = self._engine
            self.model_loaded.emit()
        else:
            try:
                engine = TranscriptionEngine(
                    model_size=self.model_size,
                    language=self.language,
                )
                self.model_loaded.emit()
            except Exception as e:
                self.error_occurred.emit(f"Failed to load model: {e}")
                return

        while not self._stop:
            try:
                chunk = self.audio_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            # Sentinel value signals shutdown
            if chunk is None:
                break

            # Exit immediately if stop was requested while waiting
            if self._stop:
                break

            try:
                segments = engine.transcribe(chunk.data)
                for seg in segments:
                    speaker = "Me" if chunk.source == "mic" else "Others"
                    logger.debug("Transcribed [%s]: %s", speaker, seg["text"][:80])
                    self.transcription_ready.emit(
                        speaker,
                        chunk.timestamp + seg["start"],
                        seg["text"],
                    )
            except Exception as e:
                logger.error("Transcription error: %s", e)
                self.error_occurred.emit(f"Transcription error: {e}")

    def stop(self):
        """Signal the worker to stop."""
        logger.info("Transcriber worker stopping")
        self._stop = True
        # Drain remaining chunks so worker doesn't process them
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        # Push sentinel to unblock the queue.get()
        try:
            self.audio_queue.put_nowait(None)
        except queue.Full:
            pass
        self.wait(10000)
