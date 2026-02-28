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

    # --- Appearance ---

    @property
    def theme(self) -> str:
        return str(self.settings.value("appearance/theme", "dark"))

    @theme.setter
    def theme(self, value: str):
        self.settings.setValue("appearance/theme", value)

    # --- Summarization ---

    @property
    def summarizer_model(self) -> str:
        return str(self.settings.value("summarization/model", "Qwen3-4B-Q4_K_M"))

    @summarizer_model.setter
    def summarizer_model(self, value: str):
        self.settings.setValue("summarization/model", value)

    # --- Recording ---
