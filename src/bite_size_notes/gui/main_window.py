"""Main application window."""

import queue
import time

from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QFont, QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from bite_size_notes.audio.capture import AudioCaptureThread
from bite_size_notes.audio.devices import get_default_mic, get_loopback_device
from bite_size_notes.gui.export_dialog import export_transcript
from bite_size_notes.gui.notes_panel import NotesPanel
from bite_size_notes.gui.settings_dialog import SettingsDialog
from bite_size_notes.gui.sidebar_panel import SidebarPanel
from bite_size_notes.gui.transcript_view import TranscriptView
from bite_size_notes.models.transcript import TranscriptSegment, TranscriptSession
from bite_size_notes.transcription.engine import TranscriptionEngine
from bite_size_notes.transcription.model_utils import is_model_cached
from bite_size_notes.transcription.worker import TranscriberWorker
from bite_size_notes.utils.config import AppConfig
from bite_size_notes.utils.platform import is_macos


class _ModelPreloadThread(QThread):
    """Background thread that loads a TranscriptionEngine into memory."""

    loaded = Signal(object)  # emits the TranscriptionEngine instance
    error = Signal(str)

    def __init__(self, model_size: str, language: str, parent=None):
        super().__init__(parent)
        self._model_size = model_size
        self._language = language

    def run(self):
        try:
            engine = TranscriptionEngine(
                model_size=self._model_size,
                language=self._language,
            )
            self.loaded.emit(engine)
        except Exception as exc:
            self.error.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bite-Size Notes")
        self.setMinimumSize(900, 500)

        self.config = AppConfig()
        self.audio_queue: queue.Queue = queue.Queue(maxsize=100)
        self.transcript_session = TranscriptSession()

        self.capture_thread: AudioCaptureThread | None = None
        self.transcriber_worker: TranscriberWorker | None = None
        self.is_recording = False
        self._record_start_time = 0.0

        self._preloaded_engine: TranscriptionEngine | None = None
        self._preload_thread: _ModelPreloadThread | None = None

        self._setup_ui()
        self._setup_toolbar()
        self._setup_status_bar()
        self._setup_timers()

        # Preload the model on startup if it's already downloaded
        if is_model_cached(self.config.model_size):
            self._preload_model()

    def _setup_ui(self):
        central = QWidget()
        central.setStyleSheet("background-color: #1e1e1e;")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Three-panel splitter ---
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #333;
                width: 1px;
            }
        """)

        # Left: sidebar
        self.sidebar = SidebarPanel()
        self.sidebar.settings_requested.connect(self._on_settings_clicked)
        self._splitter.addWidget(self.sidebar)

        # Center: transcript
        self.transcript_view = TranscriptView()
        self.transcript_view.text_edited.connect(self._on_bubble_text_edited)
        self.transcript_view.delete_requested.connect(self._on_bubble_deleted)
        self._splitter.addWidget(self.transcript_view)

        # Right: notes
        self.notes_panel = NotesPanel()
        self._splitter.addWidget(self.notes_panel)

        # Set initial sizes (sidebar 220, transcript stretches, notes 250)
        self._splitter.setSizes([220, 500, 250])
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setStretchFactor(2, 0)

        layout.addWidget(self._splitter, 1)

        # --- Bottom chat bar (placeholder) ---
        chat_bar = QWidget()
        chat_bar.setStyleSheet("background-color: #252526; border-top: 1px solid #333;")
        chat_layout = QHBoxLayout(chat_bar)
        chat_layout.setContentsMargins(8, 6, 8, 6)
        chat_layout.setSpacing(8)

        self._chat_input = QLineEdit()
        self._chat_input.setPlaceholderText("Chat input coming soon...")
        self._chat_input.setEnabled(False)
        self._chat_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #333;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
        """)
        chat_layout.addWidget(self._chat_input)

        send_btn = QPushButton("Send")
        send_btn.setEnabled(False)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: #888;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
        """)
        chat_layout.addWidget(send_btn)

        layout.addWidget(chat_bar)

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

        # Toggle sidebar
        toggle_sidebar_action = QAction("Sidebar", self)
        toggle_sidebar_action.setShortcut(QKeySequence("Ctrl+B"))
        toggle_sidebar_action.setToolTip("Toggle sidebar (Ctrl+B)")
        toggle_sidebar_action.triggered.connect(self._toggle_sidebar)
        toolbar.addAction(toggle_sidebar_action)

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

    # --- Model preloading ---

    def _preload_model(self):
        """Start loading the Whisper model in a background thread."""
        self._preloaded_engine = None
        self._preload_thread = _ModelPreloadThread(
            model_size=self.config.model_size,
            language=self.config.language,
            parent=self,
        )
        self._preload_thread.loaded.connect(self._on_model_preloaded)
        self._preload_thread.error.connect(self._on_preload_error)
        self.status_label.setText("Loading model...")
        self._preload_thread.start()

    def _on_model_preloaded(self, engine):
        self._preloaded_engine = engine
        self._preload_thread = None
        if not self.is_recording:
            self.status_label.setText("Ready")

    def _on_preload_error(self, message: str):
        self._preload_thread = None
        self.status_label.setText(f"Model load failed: {message}")

    # --- Actions ---

    def _on_record_clicked(self):
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        # Check model readiness
        if self._preloaded_engine is None:
            if self._preload_thread is not None:
                QMessageBox.information(
                    self,
                    "Model Loading",
                    "The Whisper model is still loading. Please wait a moment.",
                )
                return
            if not is_model_cached(self.config.model_size):
                QMessageBox.warning(
                    self,
                    "Model Not Downloaded",
                    f"The '{self.config.model_size}' Whisper model is not downloaded yet.\n\n"
                    "Please open Settings and click 'Download Model' first.",
                )
                return
            # Model is cached but not preloaded (e.g. preload failed) — start preload
            self._preload_model()
            QMessageBox.information(
                self,
                "Model Loading",
                "The Whisper model is loading. Please try again in a moment.",
            )
            return

        self.transcript_view.set_editable(False)

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

        # Consume preloaded engine and pass to worker
        engine = self._preloaded_engine
        self._preloaded_engine = None

        self.transcriber_worker = TranscriberWorker(
            audio_queue=self.audio_queue,
            model_size=self.config.model_size,
            language=self.config.language,
            engine=engine,
        )
        self.transcriber_worker.transcription_ready.connect(self._on_transcription)
        self.transcriber_worker.model_loaded.connect(self._on_model_loaded)
        self.transcriber_worker.error_occurred.connect(self._on_error)

        self.transcriber_worker.start()

        # Start audio capture
        self.capture_thread = AudioCaptureThread(
            mic_device_index=mic_device,
            loopback_device_index=loopback_device,
            audio_queue=self.audio_queue,
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
        self.status_label.setText("Stopped — click any bubble to edit")
        self.transcript_view.set_editable(True)
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
        self.notes_panel.clear()

    def _on_bubble_text_edited(self, index: int, new_text: str):
        """Sync an edited bubble's text back to the transcript session."""
        if 0 <= index < len(self.transcript_session.segments):
            self.transcript_session.segments[index].text = new_text

    def _on_bubble_deleted(self, index: int):
        """Remove a segment from the transcript session."""
        if 0 <= index < len(self.transcript_session.segments):
            self.transcript_session.segments.pop(index)

    def _toggle_sidebar(self):
        self.sidebar.setVisible(not self.sidebar.isVisible())

    def _on_settings_clicked(self):
        if self.is_recording:
            QMessageBox.information(
                self, "Settings", "Stop recording before changing settings."
            )
            return

        old_model = self.config.model_size
        old_language = self.config.language
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            if self.config.model_size != old_model or self.config.language != old_language:
                self._preloaded_engine = None
                if is_model_cached(self.config.model_size):
                    self._preload_model()
                else:
                    self.status_label.setText("Model not downloaded")

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
