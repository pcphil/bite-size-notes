"""Main application window."""

import queue
import time

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QFont, QKeySequence
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from bite_size_notes.audio.capture import AudioCaptureThread
from bite_size_notes.audio.devices import get_default_mic, get_loopback_device
from bite_size_notes.gui.export_dialog import export_transcript
from bite_size_notes.gui.settings_dialog import SettingsDialog
from bite_size_notes.gui.transcript_view import TranscriptView
from bite_size_notes.models.transcript import TranscriptSegment, TranscriptSession
from bite_size_notes.transcription.worker import TranscriberWorker
from bite_size_notes.utils.config import AppConfig
from bite_size_notes.utils.platform import is_macos


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bite-Size Notes")
        self.setMinimumSize(700, 500)

        self.config = AppConfig()
        self.audio_queue: queue.Queue = queue.Queue(maxsize=100)
        self.transcript_session = TranscriptSession()

        self.capture_thread: AudioCaptureThread | None = None
        self.transcriber_worker: TranscriberWorker | None = None
        self.is_recording = False
        self._record_start_time = 0.0

        self._setup_ui()
        self._setup_toolbar()
        self._setup_status_bar()
        self._setup_timers()

    def _setup_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.transcript_view = TranscriptView()
        layout.addWidget(self.transcript_view)

        self.setCentralWidget(central)

    def _setup_toolbar(self):
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)

        # Record button
        self.record_action = QAction("Record", self)
        self.record_action.setShortcut(QKeySequence("Ctrl+R"))
        self.record_action.setToolTip("Start/Stop recording (Ctrl+R)")
        self.record_action.triggered.connect(self._on_record_clicked)
        toolbar.addAction(self.record_action)

        toolbar.addSeparator()

        # Export button
        export_action = QAction("Export", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.setToolTip("Export transcript (Ctrl+E)")
        export_action.triggered.connect(self._on_export_clicked)
        toolbar.addAction(export_action)

        # Clear button
        clear_action = QAction("Clear", self)
        clear_action.triggered.connect(self._on_clear_clicked)
        toolbar.addAction(clear_action)

        toolbar.addSeparator()

        # Settings button
        settings_action = QAction("Settings", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.setToolTip("Open settings (Ctrl+,)")
        settings_action.triggered.connect(self._on_settings_clicked)
        toolbar.addAction(settings_action)

    def _setup_status_bar(self):
        self.status_label = QLabel("Ready")
        self.statusBar().addWidget(self.status_label, 1)

        self.duration_label = QLabel("")
        self.statusBar().addPermanentWidget(self.duration_label)

        # Mic level meter
        self.mic_level = QProgressBar()
        self.mic_level.setMaximumWidth(80)
        self.mic_level.setMaximumHeight(14)
        self.mic_level.setRange(0, 100)
        self.mic_level.setFormat("Mic")
        self.mic_level.setTextVisible(True)
        self.statusBar().addPermanentWidget(self.mic_level)

        # Loopback level meter
        self.loopback_level = QProgressBar()
        self.loopback_level.setMaximumWidth(80)
        self.loopback_level.setMaximumHeight(14)
        self.loopback_level.setRange(0, 100)
        self.loopback_level.setFormat("Sys")
        self.loopback_level.setTextVisible(True)
        self.statusBar().addPermanentWidget(self.loopback_level)

    def _setup_timers(self):
        # Timer to update duration and audio levels
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self._update_ui)
        self.ui_timer.setInterval(200)

    # --- Actions ---

    def _on_record_clicked(self):
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        # Resolve devices
        mic_device = self.config.mic_device
        if mic_device == -1:
            default_mic = get_default_mic()
            if default_mic is None:
                QMessageBox.critical(
                    self, "Error", "No microphone found. Check Settings."
                )
                return
            mic_device = default_mic.index

        loopback_device = self.config.loopback_device
        if loopback_device == -1:
            # Try auto-detect
            lb = get_loopback_device()
            if lb is not None:
                loopback_device = lb.index
            else:
                loopback_device = None
                if is_macos():
                    QMessageBox.warning(
                        self,
                        "BlackHole Not Found",
                        "BlackHole virtual audio driver was not detected.\n\n"
                        "System audio (other participants) will not be captured.\n"
                        "Install BlackHole from: https://github.com/ExistentialAudio/BlackHole",
                    )

        # Clear queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

        # Start transcription worker first (so it's ready for chunks)
        self.transcriber_worker = TranscriberWorker(
            audio_queue=self.audio_queue,
            model_size=self.config.model_size,
            language=self.config.language,
        )
        self.transcriber_worker.transcription_ready.connect(self._on_transcription)
        self.transcriber_worker.model_loaded.connect(self._on_model_loaded)
        self.transcriber_worker.error_occurred.connect(self._on_error)

        self.status_label.setText("Loading Whisper model...")
        self.transcriber_worker.start()

        # Start audio capture
        self.capture_thread = AudioCaptureThread(
            mic_device_index=mic_device,
            loopback_device_index=loopback_device,
            audio_queue=self.audio_queue,
            chunk_seconds=self.config.chunk_seconds,
        )
        self.capture_thread.start()

        self.is_recording = True
        self._record_start_time = time.monotonic()
        self.record_action.setText("Stop")
        self.ui_timer.start()

    def _stop_recording(self):
        self.ui_timer.stop()

        if self.capture_thread is not None:
            self.capture_thread.stop()
            self.capture_thread.join(timeout=3.0)
            self.capture_thread = None

        if self.transcriber_worker is not None:
            self.transcriber_worker.stop()
            self.transcriber_worker = None

        self.is_recording = False
        self.record_action.setText("Record")
        self.status_label.setText("Stopped")
        self.duration_label.setText("")
        self.mic_level.setValue(0)
        self.loopback_level.setValue(0)

    def _on_transcription(self, speaker: str, timestamp: float, text: str):
        """Slot: new transcription segment received."""
        segment = TranscriptSegment(
            text=text,
            source="mic" if speaker == "Me" else "loopback",
            timestamp=timestamp,
            speaker_label=speaker,
        )
        self.transcript_session.add_segment(segment)
        self.transcript_view.append_segment(segment)

    def _on_model_loaded(self):
        self.status_label.setText("Recording...")

    def _on_error(self, message: str):
        self.status_label.setText(f"Error: {message}")

    def _on_export_clicked(self):
        export_transcript(self.transcript_session, self)

    def _on_clear_clicked(self):
        self.transcript_session.clear()
        self.transcript_view.clear_transcript()

    def _on_settings_clicked(self):
        if self.is_recording:
            QMessageBox.information(
                self, "Settings", "Stop recording before changing settings."
            )
            return
        dialog = SettingsDialog(self.config, self)
        dialog.exec()

    def _update_ui(self):
        """Periodic UI update for duration and audio levels."""
        if self.is_recording:
            elapsed = time.monotonic() - self._record_start_time
            m = int(elapsed // 60)
            s = int(elapsed % 60)
            self.duration_label.setText(f"{m:02d}:{s:02d}")

            if self.capture_thread is not None:
                # RMS to percentage (0-100), clamped
                mic_pct = min(100, int(self.capture_thread.mic_rms * 500))
                lb_pct = min(100, int(self.capture_thread.loopback_rms * 500))
                self.mic_level.setValue(mic_pct)
                self.loopback_level.setValue(lb_pct)

    def closeEvent(self, event):
        """Clean up threads on window close."""
        if self.is_recording:
            self._stop_recording()
        event.accept()
