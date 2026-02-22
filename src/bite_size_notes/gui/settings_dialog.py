"""Settings dialog for device and model configuration."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from bite_size_notes.audio.devices import (
    list_input_devices,
    list_loopback_devices,
)
from bite_size_notes.utils.config import AppConfig


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

        self.lang_combo = QComboBox()
        for name, code in self.LANGUAGES:
            self.lang_combo.addItem(name, code)
        trans_layout.addRow("Language:", self.lang_combo)

        self.chunk_spin = QSpinBox()
        self.chunk_spin.setRange(3, 30)
        self.chunk_spin.setSuffix(" seconds")
        trans_layout.addRow("Chunk Duration:", self.chunk_spin)

        trans_group.setLayout(trans_layout)
        layout.addWidget(trans_group)

        # --- Buttons ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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

        # Chunk duration
        self.chunk_spin.setValue(int(self.config.chunk_seconds))

    def _save_and_accept(self):
        self.config.mic_device = self.mic_combo.currentData()
        self.config.loopback_device = self.loopback_combo.currentData()
        self.config.model_size = self.model_combo.currentText()
        self.config.language = self.lang_combo.currentData() or "en"
        self.config.chunk_seconds = float(self.chunk_spin.value())
        self.accept()
