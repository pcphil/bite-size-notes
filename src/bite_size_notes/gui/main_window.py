"""Main application window."""

import queue
import time

from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from bite_size_notes.audio.capture import AudioCaptureThread
from bite_size_notes.gui.themes import build_stylesheet, get_palette
from bite_size_notes.audio.devices import get_default_mic, get_loopback_device
from bite_size_notes.gui.export_dialog import export_output, export_transcript
from bite_size_notes.gui.notes_panel import NotesPanel
from bite_size_notes.gui.output_panel import OutputPanel
from bite_size_notes.gui.settings_dialog import SettingsDialog
from bite_size_notes.gui.sidebar_panel import SidebarPanel
from bite_size_notes.gui.transcript_view import TranscriptView
from bite_size_notes.models.session_store import SessionStore
from bite_size_notes.models.transcript import TranscriptSegment, TranscriptSession
from bite_size_notes.summarization.engine import (
    is_summarizer_cached,
    load_summarizer,
    summarize,
)
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


class _SummarizeThread(QThread):
    """Background thread that runs summarization on transcript text."""

    finished = Signal(str)
    error = Signal(str)

    def __init__(self, transcript_text: str, parent=None):
        super().__init__(parent)
        self._text = transcript_text

    def run(self):
        try:
            llm = load_summarizer()
            result = summarize(llm, self._text)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self, app=None):
        super().__init__()
        self._app = app
        self.setWindowTitle("Bite-Size Notes")
        self.setMinimumSize(900, 500)

        self.config = AppConfig()
        self.audio_queue: queue.Queue = queue.Queue(maxsize=100)
        self.session_store = SessionStore()
        self.transcript_session = TranscriptSession()

        self.capture_thread: AudioCaptureThread | None = None
        self.transcriber_worker: TranscriberWorker | None = None
        self.is_recording = False
        self._record_start_time = 0.0

        self._preloaded_engine: TranscriptionEngine | None = None
        self._preload_thread: _ModelPreloadThread | None = None
        self._summarize_thread: _SummarizeThread | None = None

        self._setup_ui()
        self._setup_status_bar()
        self._setup_timers()

        # Populate sidebar with saved sessions
        self.sidebar.refresh_sessions(active_id=self.transcript_session.id)

        # Preload the model on startup if it's already downloaded
        if is_model_cached(self.config.model_size):
            self._preload_model()

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Three-panel splitter ---
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: sidebar
        self.sidebar = SidebarPanel(self.session_store)
        self.sidebar.settings_requested.connect(self._on_settings_clicked)
        self.sidebar.session_selected.connect(self._on_session_selected)
        self.sidebar.new_session_requested.connect(self._on_new_session)
        self.sidebar.delete_session_requested.connect(self._on_delete_session)
        self._splitter.addWidget(self.sidebar)

        # Center: transcript
        self.transcript_view = TranscriptView()
        self.transcript_view.text_edited.connect(self._on_bubble_text_edited)
        self.transcript_view.delete_requested.connect(self._on_bubble_deleted)
        self._splitter.addWidget(self.transcript_view)

        # Right: output
        self.output_panel = OutputPanel()
        self._splitter.addWidget(self.output_panel)

        # Set initial sizes (sidebar 220, transcript stretches, output 350)
        self._splitter.setSizes([220, 400, 350])
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setStretchFactor(2, 0)

        layout.addWidget(self._splitter, 1)

        # Connect sidebar collapse to redistribute splitter space
        self._saved_splitter_sizes = self._splitter.sizes()
        self._saved_output_sizes = self._splitter.sizes()
        self.sidebar.collapse_toggled.connect(self._on_sidebar_collapse_toggled)

        # Connect transcript view control signals
        self.transcript_view.record_clicked.connect(self._on_record_clicked)
        self.transcript_view.clear_clicked.connect(self._on_clear_clicked)
        self.transcript_view.export_clicked.connect(self._on_export_clicked)

        # Connect output panel signals
        self.output_panel.notes_toggled.connect(self._toggle_notes)
        self.output_panel.export_output_clicked.connect(self._on_export_output_clicked)
        self.output_panel.collapse_toggled.connect(self._on_output_collapse_toggled)
        self.output_panel.bite_size_clicked.connect(self._on_bite_size_clicked)

        # Connect sidebar rename signal
        self.sidebar.rename_session_requested.connect(self._on_rename_session)

        self.setCentralWidget(central)

        # Keyboard shortcut for record (Ctrl+R)
        record_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        record_shortcut.activated.connect(self._on_record_clicked)

        # --- Floating notes panel (parented to central widget, positioned later) ---
        self.notes_panel = NotesPanel(central)
        self.notes_panel.close_requested.connect(self._toggle_notes)

    def _setup_status_bar(self):
        self.status_label = QLabel("Ready for Recording")
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
        self.status_label.setText("Loading transcriber...")
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
        self.transcript_view.set_recording(True)
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
        self.transcript_view.set_recording(False)
        self.status_label.setText("Stopped — click any bubble to edit")
        self.transcript_view.set_editable(True)
        self.duration_label.setText("")
        self.mic_level.setValue(0)
        self.loopback_level.setValue(0)

        # Auto-save session if it has content
        if self.transcript_session.segments:
            self.session_store.save_session(self.transcript_session)
            self.sidebar.refresh_sessions(active_id=self.transcript_session.id)

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

    def _on_export_output_clicked(self):
        export_output(self.output_panel.text(), self)

    def _on_clear_clicked(self):
        self.transcript_session.clear()
        self.transcript_view.clear_transcript()
        self.notes_panel.clear()

    def _on_bite_size_clicked(self):
        """Handle the Bite Size It button click."""
        if not is_summarizer_cached():
            QMessageBox.warning(
                self,
                "Summarizer Not Downloaded",
                "The Qwen3 summarizer model is not downloaded yet.\n\n"
                "Please open Settings and click 'Download Model' in the "
                "Summarizer Model section.",
            )
            return

        text = self.transcript_session.to_text()
        if not text.strip():
            QMessageBox.information(
                self, "No Transcript", "There is no transcript to summarize."
            )
            return

        if self._summarize_thread is not None:
            return  # already running

        self.output_panel.set_text("Summarizing...")
        self._summarize_thread = _SummarizeThread(text, self)
        self._summarize_thread.finished.connect(self._on_summarize_finished)
        self._summarize_thread.error.connect(self._on_summarize_error)
        self._summarize_thread.start()

    def _on_summarize_finished(self, result: str):
        self._summarize_thread = None
        self.output_panel.set_text(result)
        self.transcript_session.summary = result
        if self.transcript_session.segments:
            self.session_store.save_session(self.transcript_session)

    def _on_summarize_error(self, message: str):
        self._summarize_thread = None
        self.output_panel.set_text(f"Summarization failed: {message}")

    def _on_bubble_text_edited(self, index: int, new_text: str):
        """Sync an edited bubble's text back to the transcript session."""
        if 0 <= index < len(self.transcript_session.segments):
            self.transcript_session.segments[index].text = new_text

    def _on_bubble_deleted(self, index: int):
        """Remove a segment from the transcript session."""
        if 0 <= index < len(self.transcript_session.segments):
            self.transcript_session.segments.pop(index)

    def _on_session_selected(self, session_id: str):
        """Load a previously-saved session into the transcript view."""
        if self.is_recording:
            return
        try:
            session = self.session_store.load_session(session_id)
        except Exception:
            return
        self.transcript_session = session
        self.transcript_view.clear_transcript()
        for segment in session.segments:
            self.transcript_view.append_segment(segment)
        self.transcript_view.set_editable(True)
        if session.summary:
            self.output_panel.set_text(session.summary)
        else:
            self.output_panel.clear()
        self.sidebar.set_active_session(session_id)

    def _on_new_session(self):
        """Save current session (if non-empty) and start a fresh one."""
        if self.is_recording:
            return
        if self.transcript_session.segments:
            self.session_store.save_session(self.transcript_session)
        self.transcript_session = TranscriptSession()
        self.transcript_view.clear_transcript()
        self.transcript_view.set_editable(False)
        self.notes_panel.clear()
        self.output_panel.clear()
        self.sidebar.refresh_sessions(active_id=self.transcript_session.id)

    def _on_rename_session(self, session_id: str):
        """Prompt the user to rename a session."""
        try:
            session = self.session_store.load_session(session_id)
        except Exception:
            return
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Session",
            "New name:",
            text=session.title,
        )
        if not ok or not new_name.strip():
            return
        session.title = new_name.strip()
        self.session_store.save_session(session)
        if session_id == self.transcript_session.id:
            self.transcript_session.title = session.title
        self.sidebar.refresh_sessions(active_id=self.transcript_session.id)

    def _on_delete_session(self, session_id: str):
        """Delete a session after confirmation."""
        reply = QMessageBox.question(
            self,
            "Delete Session",
            "Are you sure you want to delete this session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.session_store.delete_session(session_id)
        # If the deleted session is the current one, start fresh
        if session_id == self.transcript_session.id:
            self.transcript_session = TranscriptSession()
            self.transcript_view.clear_transcript()
            self.notes_panel.clear()
        self.sidebar.refresh_sessions(active_id=self.transcript_session.id)

    def _toggle_notes(self):
        if self.notes_panel.isVisible():
            self.notes_panel.hide()
        else:
            self._position_notes_panel()
            self.notes_panel.show()
            self.notes_panel.raise_()

    def _on_sidebar_collapse_toggled(self, collapsed: bool):
        """Redistribute splitter space when the sidebar collapses/expands."""
        sizes = self._splitter.sizes()
        total = sum(sizes)
        if collapsed:
            self._saved_splitter_sizes = sizes
            self._splitter.setSizes([40, total - 40 - sizes[2], sizes[2]])
        else:
            # Restore previous proportions
            self._splitter.setSizes(self._saved_splitter_sizes)

    def _on_output_collapse_toggled(self, collapsed: bool):
        """Redistribute splitter space when the output panel collapses/expands."""
        sizes = self._splitter.sizes()
        total = sum(sizes)
        if collapsed:
            self._saved_output_sizes = sizes
            self._splitter.setSizes([sizes[0], total - sizes[0] - 40, 40])
        else:
            self._splitter.setSizes(self._saved_output_sizes)

    def _position_notes_panel(self):
        """Anchor the notes panel at the bottom-right of the central widget."""
        central = self.centralWidget()
        if central is None:
            return
        margin = 12
        x = central.width() - self.notes_panel.width() - margin
        y = central.height() - self.notes_panel.height() - margin
        self.notes_panel.move(max(x, 0), max(y, 0))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.notes_panel.isVisible():
            self._position_notes_panel()

    def _on_settings_clicked(self):
        if self.is_recording:
            QMessageBox.information(
                self, "Settings", "Stop recording before changing settings."
            )
            return

        old_model = self.config.model_size
        old_language = self.config.language
        old_theme = self.config.theme
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            # Reapply theme if changed
            if self.config.theme != old_theme and self._app is not None:
                self._app.setStyleSheet(
                    build_stylesheet(get_palette(self.config.theme))
                )
            if (
                self.config.model_size != old_model
                or self.config.language != old_language
            ):
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
        """Clean up threads on window close and save current session."""
        if self.is_recording:
            self._stop_recording()
        if self.transcript_session.segments:
            self.session_store.save_session(self.transcript_session)
        event.accept()
