"""Settings dialog for device and model configuration."""

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from bite_size_notes.audio.devices import (
    list_input_devices,
    list_loopback_devices,
)
from bite_size_notes.transcription.model_utils import (
    download_model_sync,
    is_model_cached,
)
from bite_size_notes.utils.config import AppConfig


class _ModelDownloadThread(QThread):
    """Background thread that downloads a Whisper model."""

    finished = Signal(str)  # emits cached path on success
    error = Signal(str)  # emits error message on failure

    def __init__(self, model_size: str, parent=None):
        super().__init__(parent)
        self._model_size = model_size

    def run(self):
        try:
            path = download_model_sync(self._model_size)
            self.finished.emit(path)
        except Exception as exc:
            self.error.emit(str(exc))


class SettingsDialog(QDialog):
    """Dialog for configuring audio devices and transcription settings."""

    MODELS = ["tiny", "base", "small", "medium"]
    LANGUAGES = [
        ("English", "en"),
        ("Spanish", "es"),
        ("French", "fr"),
        ("German", "de"),
        ("Chinese", "zh"),
        ("Japanese", "ja"),
        ("Korean", "ko"),
        ("Portuguese", "pt"),
        ("Auto-detect", None),
    ]

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._download_thread: _ModelDownloadThread | None = None
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # --- Audio devices ---
        audio_group = QGroupBox("Audio Devices")
        audio_layout = QFormLayout()

        self.mic_combo = QComboBox()
        audio_layout.addRow("Microphone:", self.mic_combo)

        self.loopback_combo = QComboBox()
        audio_layout.addRow("System Audio (Loopback):", self.loopback_combo)

        self.refresh_btn_label = QLabel('<a href="#">Refresh devices</a>')
        self.refresh_btn_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.refresh_btn_label.linkActivated.connect(self._refresh_devices)
        audio_layout.addRow("", self.refresh_btn_label)

        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)

        # --- Transcription ---
        trans_group = QGroupBox("Transcription")
        trans_layout = QFormLayout()

        self.model_combo = QComboBox()
        self.model_combo.addItems(self.MODELS)
        trans_layout.addRow("Whisper Model:", self.model_combo)

        # Model download row: status label + download button
        model_dl_row = QHBoxLayout()
        self._model_status = QLabel()
        model_dl_row.addWidget(self._model_status)
        model_dl_row.addStretch()
        self._download_btn = QPushButton("Download Model")
        self._download_btn.clicked.connect(self._start_download)
        model_dl_row.addWidget(self._download_btn)
        trans_layout.addRow("", model_dl_row)

        self.model_combo.currentTextChanged.connect(self._update_model_status)

        self.lang_combo = QComboBox()
        for name, code in self.LANGUAGES:
            self.lang_combo.addItem(name, code)
        trans_layout.addRow("Language:", self.lang_combo)

        trans_group.setLayout(trans_layout)
        layout.addWidget(trans_group)

        # --- Buttons ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_model_status(self):
        """Check whether the currently selected model is cached and update the label."""
        model = self.model_combo.currentText()
        if is_model_cached(model):
            self._model_status.setText("Ready")
            self._model_status.setStyleSheet("color: green; font-weight: bold;")
            self._download_btn.setEnabled(False)
        else:
            self._model_status.setText("Not downloaded")
            self._model_status.setStyleSheet("color: orange; font-weight: bold;")
            self._download_btn.setEnabled(True)

    def _start_download(self):
        """Download the selected model in a background thread."""
        model = self.model_combo.currentText()
        self._download_btn.setEnabled(False)
        self._model_status.setText("Downloading...")
        self._model_status.setStyleSheet("color: gray; font-weight: bold;")

        self._download_thread = _ModelDownloadThread(model, self)
        self._download_thread.finished.connect(self._on_download_finished)
        self._download_thread.error.connect(self._on_download_error)
        self._download_thread.start()

    def _on_download_finished(self, _path: str):
        self._download_thread = None
        self._update_model_status()

    def _on_download_error(self, message: str):
        self._download_thread = None
        self._model_status.setText("Download failed")
        self._model_status.setStyleSheet("color: red; font-weight: bold;")
        self._download_btn.setEnabled(True)

    def _refresh_devices(self):
        """Re-enumerate audio devices."""
        self.mic_combo.clear()
        self.loopback_combo.clear()

        self.mic_combo.addItem("(Default)", -1)
        for dev in list_input_devices():
            if not dev.is_loopback:
                self.mic_combo.addItem(dev.name, dev.index)

        self.loopback_combo.addItem("(None - mic only)", -1)
        for dev in list_loopback_devices():
            self.loopback_combo.addItem(dev.name, dev.index)

    def _load_settings(self):
        self._refresh_devices()

        # Restore saved mic device
        mic_idx = self.mic_combo.findData(self.config.mic_device)
        if mic_idx >= 0:
            self.mic_combo.setCurrentIndex(mic_idx)

        # Restore saved loopback device
        lb_idx = self.loopback_combo.findData(self.config.loopback_device)
        if lb_idx >= 0:
            self.loopback_combo.setCurrentIndex(lb_idx)

        # Model
        model_idx = self.model_combo.findText(self.config.model_size)
        if model_idx >= 0:
            self.model_combo.setCurrentIndex(model_idx)

        # Language
        lang_idx = self.lang_combo.findData(self.config.language)
        if lang_idx >= 0:
            self.lang_combo.setCurrentIndex(lang_idx)

        # Initial model status check
        self._update_model_status()

    def _save_and_accept(self):
        self.config.mic_device = self.mic_combo.currentData()
        self.config.loopback_device = self.loopback_combo.currentData()
        self.config.model_size = self.model_combo.currentText()
        self.config.language = self.lang_combo.currentData() or "en"
        self.accept()
