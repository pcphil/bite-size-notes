# End-to-End Data Flow

This document traces data through the application — from audio capture to transcript display to summarization output.

See also: [Architecture Overview](architecture.md) | [Platform Guide](platform-guide.md)

## Recording Flow

When the user clicks the record button (or presses `Ctrl+R`), the following sequence executes:

```
User clicks Record
        │
        ▼
MainWindow._on_record_clicked()
        │
        ▼
MainWindow._start_recording()
        │
        ├── Check _preloaded_engine is ready
        ├── Resolve mic device (AppConfig or auto-detect via get_default_mic())
        ├── Resolve loopback device (AppConfig or auto-detect via get_loopback_device())
        ├── Drain audio_queue
        │
        ├── Create TranscriberWorker(audio_queue, engine=_preloaded_engine)
        │       └── Connect signals:
        │           ├── transcription_ready → _on_transcription
        │           ├── model_loaded → _on_model_loaded
        │           └── error_occurred → _on_error
        │       └── worker.start()
        │
        ├── Create AudioCaptureThread(mic_index, loopback_index, audio_queue)
        │       └── capture_thread.start()
        │
        └── Start 200ms UI timer → _update_ui()
```

### During Recording

```
  ┌──────────────────────────────────────────────────────────────────┐
  │                     AudioCaptureThread                          │
  │                                                                 │
  │  ┌─────────────────┐              ┌──────────────────────────┐  │
  │  │ Mic Stream       │              │ Loopback Stream          │  │
  │  │ (sounddevice)    │              │ (WASAPI / sounddevice)   │  │
  │  │                  │              │                          │  │
  │  │ _mic_callback()  │              │ _loopback_callback() or  │  │
  │  │   │              │              │ _start_wasapi_loopback() │  │
  │  │   ▼              │              │   │                      │  │
  │  │ _mic_buffer      │              │   ▼                      │  │
  │  │ (Lock-protected) │              │ _loopback_buffer         │  │
  │  └────────┬─────────┘              │ (Lock-protected)         │  │
  │           │                        └──────────┬───────────────┘  │
  │           │                                   │                  │
  │           └──────────┬────────────────────────┘                  │
  │                      │                                           │
  │                      ▼                                           │
  │           Silence detection loop (100ms poll)                    │
  │           ├── Compute RMS for each buffer                        │
  │           ├── If speech → silence > 1.0s:                        │
  │           │     Flush buffer as AudioChunk (min 16000 samples)   │
  │           └── _safe_put(chunk) into queue                        │
  └──────────────────────┬───────────────────────────────────────────┘
                         │
                         ▼
               queue.Queue(maxsize=100)
               (drops oldest when full)
                         │
                         ▼
  ┌──────────────────────────────────────────────────┐
  │              TranscriberWorker (QThread)          │
  │                                                  │
  │  Pulls AudioChunk with 1s timeout                │
  │         │                                        │
  │         ▼                                        │
  │  engine.transcribe(chunk.data)                   │
  │  (faster-whisper with VAD, beam_size=5)          │
  │         │                                        │
  │         ▼                                        │
  │  For each segment:                               │
  │    speaker = "Me" if mic, "Others" if loopback   │
  │    emit transcription_ready(speaker, ts, text)   │
  └────────────────────┬─────────────────────────────┘
                       │
                       ▼  (Qt signal, cross-thread)
  ┌──────────────────────────────────────────────────┐
  │              MainWindow (main thread)            │
  │                                                  │
  │  _on_transcription(speaker, timestamp, text)     │
  │    ├── Create TranscriptSegment                  │
  │    ├── Append to transcript_session.segments     │
  │    └── transcript_view.append_segment(segment)   │
  │           └── Add TranscriptLineWidget           │
  │               (color-coded by speaker)           │
  └──────────────────────────────────────────────────┘
```

### Audio Format

All audio throughout the pipeline is:
- **Sample rate**: 16,000 Hz
- **Channels**: Mono (1)
- **Dtype**: float32
- **Range**: -1.0 to 1.0

WASAPI loopback audio is resampled from the device's native sample rate to 16 kHz using linear interpolation (`np.interp`), and multi-channel audio is averaged to mono.

### Stop Recording

```
User clicks Stop (or Ctrl+R)
        │
        ▼
MainWindow._stop_recording()
        │
        ├── Stop UI timer
        ├── capture_thread.stop()     ← sets _stop_event, join(3s)
        ├── transcriber_worker.stop() ← drains queue, pushes None sentinel, wait(10s)
        └── Auto-save session if it has segments
```

## Threading Model

```
┌─────────────────────────────────────────────────────────────────┐
│                        MAIN THREAD                              │
│                     (Qt event loop)                              │
│                                                                 │
│  MainWindow ◄── Qt signals ──┐                                  │
│  TranscriptView              │                                  │
│  SidebarPanel                │                                  │
│  OutputPanel                 │                                  │
│  NotesPanel                  │                                  │
│  SettingsDialog              │                                  │
└──────────────────────────────┼──────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐  ┌───────────────────┐  ┌────────────────────┐
│ Transcriber   │  │ _ModelPreload     │  │ _Summarize         │
│ Worker        │  │ Thread            │  │ Thread             │
│ (QThread)     │  │ (QThread)         │  │ (QThread)          │
│               │  │                   │  │                    │
│ Signals:      │  │ Signals:          │  │ Signals:           │
│ transcription │  │ loaded(engine)    │  │ finished(str)      │
│ _ready()      │  │ error(str)        │  │ error(str)         │
│ model_loaded()│  └───────────────────┘  └────────────────────┘
│ error()       │
└───────┬───────┘
        │ reads from
        ▼
  queue.Queue(100)
        ▲
        │ writes to
┌───────┴────────────────────────────────────────────┐
│              AudioCaptureThread                    │
│              (threading.Thread, daemon)            │
│                                                    │
│  ┌──────────────┐    ┌───────────────────────────┐ │
│  │ sounddevice   │    │ WASAPI loopback thread    │ │
│  │ callbacks     │    │ (threading.Thread, daemon) │ │
│  │ (OS threads)  │    │ [Windows only]            │ │
│  └──────────────┘    └───────────────────────────┘ │
└────────────────────────────────────────────────────┘
```

### Thread Communication

| Mechanism | Between | Purpose |
|---|---|---|
| `queue.Queue(maxsize=100)` | AudioCaptureThread → TranscriberWorker | Passes `AudioChunk` objects; drops oldest when full |
| `threading.Lock` | OS audio callbacks → AudioCaptureThread | Protects `_mic_buffer` and `_loopback_buffer` |
| `threading.Event` | MainWindow → AudioCaptureThread | `_stop_event` signals the capture loop to exit |
| `threading.Event` | AudioCaptureThread → WASAPI thread | `_wasapi_stop_event` stops the loopback sub-thread |
| Qt `Signal` | TranscriberWorker → MainWindow | `transcription_ready`, `model_loaded`, `error_occurred` |
| Qt `Signal` | _ModelPreloadThread → MainWindow | `loaded(engine)`, `error(str)` |
| Qt `Signal` | _SummarizeThread → MainWindow | `finished(str)`, `error(str)` |
| `None` sentinel in queue | TranscriberWorker.stop() → run() | Unblocks the `queue.get(timeout=1)` call to exit the loop |

## Summarization Flow

```
User clicks "Bite Size It"
        │
        ▼
MainWindow._on_bite_size_clicked()
        │
        ├── Check is_summarizer_cached() — abort with dialog if not downloaded
        ├── Build text from transcript_session.to_text()
        │     └── Append NotesPanel text if present
        ├── Set output_panel text to "Summarizing..."
        │
        ▼
_SummarizeThread(text).start()
        │
        ├── load_summarizer()
        │     └── hf_hub_download("unsloth/Qwen3-4B-GGUF", "Qwen3-4B-Q4_K_M.gguf")
        │     └── Llama(model_path, n_ctx=2048, verbose=False)
        │
        ├── summarize(llm, text)
        │     └── llm.create_chat_completion(
        │           system=SYSTEM_PROMPT,       ← structured meeting-notes format
        │           user=text + "/no_think",     ← suppresses chain-of-thought
        │           max_tokens=512,
        │           temperature=0.7
        │         )
        │     └── Strip <think>...</think> blocks via regex
        │
        ▼
emit finished(summary_text)
        │
        ▼  (Qt signal → main thread)
MainWindow._on_summarize_finished(text)
        ├── output_panel.set_text(text)
        ├── transcript_session.summary = text
        └── session_store.save_session(transcript_session)
```

## Session Management Flow

### Lifecycle

```
App starts
    │
    ├── SessionStore.__init__()
    │     └── Create sessions directory if missing
    │     └── _migrate_from_old_org() (one-time migration)
    │
    ├── MainWindow.__init__()
    │     └── Create blank TranscriptSession
    │     └── Populate sidebar via session_store.list_sessions()
    │
    ▼
User interacts with sessions:

  ┌─ New Session ──────────────────────────────────────────────┐
  │  Sidebar "+" → _on_new_session()                          │
  │  ├── Save current session if non-empty                    │
  │  ├── Create fresh TranscriptSession()                     │
  │  ├── Save blank session immediately                       │
  │  └── Refresh sidebar                                      │
  └────────────────────────────────────────────────────────────┘

  ┌─ Load Session ─────────────────────────────────────────────┐
  │  Sidebar item click → _on_session_selected(id)            │
  │  ├── session_store.load_session(id)                       │
  │  ├── Clear transcript view                                │
  │  ├── Append all segments as TranscriptLineWidgets         │
  │  ├── Set editable mode                                    │
  │  └── Show summary in output panel if present              │
  └────────────────────────────────────────────────────────────┘

  ┌─ Rename Session ───────────────────────────────────────────┐
  │  Sidebar ✏ button → _on_rename_session(id)                │
  │  ├── QInputDialog.getText for new title                   │
  │  ├── Update session.title, save                           │
  │  └── Refresh sidebar                                      │
  └────────────────────────────────────────────────────────────┘

  ┌─ Delete Session ───────────────────────────────────────────┐
  │  Sidebar × button → _on_delete_session(id)                │
  │  ├── QMessageBox confirmation                             │
  │  ├── session_store.delete_session(id)                     │
  │  ├── If active session deleted → start fresh              │
  │  └── Refresh sidebar                                      │
  └────────────────────────────────────────────────────────────┘
```

### Auto-Save Triggers

| Event | Trigger |
|---|---|
| Recording stopped | `_stop_recording()` saves if segments exist |
| Summarization complete | `_on_summarize_finished()` saves with summary |
| Application closed | `closeEvent()` saves if segments exist |

### Session File Format

Each session is a JSON file at `{AppData}/pcphil/Bite-Size-Notes/sessions/{uuid}.json`:

```json
{
  "id": "uuid4-string",
  "title": "Meeting — 2026-02-28 14:30",
  "summary": "...",
  "start_time": "2026-02-28T14:30:00",
  "segments": [
    {
      "text": "Hello everyone",
      "source": "mic",
      "timestamp": 3.5,
      "speaker_label": "Me"
    }
  ]
}
```

## Application Lifecycle

### Startup

```
Entry point
├── `uv run bite-size-notes` → pyproject.toml [project.scripts] → app:main
├── `python -m bite_size_notes` → __main__.py → app.main()
└── PyInstaller .exe → app.py (sys.frozen=True)

main()
  └── _main_inner()  (wrapped in try/except for crash handling)
        │
        ├── QApplication(sys.argv)
        │     setApplicationName("Bite-Size Notes")
        │     setOrganizationName("pcphil")
        │
        ├── AppConfig() → load theme
        │     build_stylesheet(get_palette(config.theme))
        │
        ├── QSplashScreen with logo.ico
        │
        ├── MainWindow(app=app)
        │     ├── Create AppConfig, audio_queue(100), SessionStore
        │     ├── Create blank TranscriptSession
        │     ├── _setup_ui()
        │     │     └── QSplitter [220, 400, 350]
        │     │         ├── SidebarPanel
        │     │         ├── TranscriptView
        │     │         └── OutputPanel
        │     │     └── NotesPanel (floating overlay, hidden)
        │     ├── _setup_status_bar()
        │     │     └── status_label, duration_label, mic_level, loopback_level
        │     ├── _setup_timers()
        │     ├── Populate sidebar
        │     └── Preload model if cached → _ModelPreloadThread.start()
        │
        ├── window.show()
        ├── splash.finish(window)
        └── sys.exit(app.exec())
```

### Shutdown

```
Window close (X button or Alt+F4)
        │
        ▼
MainWindow.closeEvent()
        │
        ├── If recording:
        │     └── _stop_recording()
        │         ├── capture_thread.stop() + join(3s)
        │         └── transcriber_worker.stop() + wait(10s)
        │
        ├── Save session if segments exist
        └── event.accept()
```

### Crash Handler

If `_main_inner()` raises an unhandled exception:
1. Writes traceback to `%APPDATA%/Bite-Size Notes/crash.log`
2. Attempts `QMessageBox.critical` dialog
3. Falls back to `ctypes.windll.user32.MessageBoxW` on Windows
4. If frozen (PyInstaller), prints traceback and waits for Enter key

---

See also: [Architecture Overview](architecture.md) | [Platform Guide](platform-guide.md)
