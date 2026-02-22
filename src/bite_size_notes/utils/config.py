"""Application settings persistence."""

from PySide6.QtCore import QSettings


class AppConfig:
    """Persistent settings backed by QSettings."""

    def __init__(self):
        self.settings = QSettings("BiteSize", "Bite-Size-Notes")

    # --- Audio devices ---

    @property
    def mic_device(self) -> int:
        return int(self.settings.value("audio/mic_device", -1))

    @mic_device.setter
    def mic_device(self, value: int):
        self.settings.setValue("audio/mic_device", value)

    @property
    def loopback_device(self) -> int:
        return int(self.settings.value("audio/loopback_device", -1))

    @loopback_device.setter
    def loopback_device(self, value: int):
        self.settings.setValue("audio/loopback_device", value)

    # --- Transcription ---

    @property
    def model_size(self) -> str:
        return str(self.settings.value("transcription/model_size", "base"))

    @model_size.setter
    def model_size(self, value: str):
        self.settings.setValue("transcription/model_size", value)

    @property
    def language(self) -> str:
        return str(self.settings.value("transcription/language", "en"))

    @language.setter
    def language(self, value: str):
        self.settings.setValue("transcription/language", value)

    # --- Recording ---

    @property
    def chunk_seconds(self) -> float:
        return float(self.settings.value("recording/chunk_seconds", 5.0))

    @chunk_seconds.setter
    def chunk_seconds(self, value: float):
        self.settings.setValue("recording/chunk_seconds", value)
