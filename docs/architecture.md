# Architecture Overview

Bite-Size Notes is a desktop meeting transcriber that captures microphone and system audio simultaneously, runs local Whisper speech-to-text (via faster-whisper), summarizes transcripts with a local LLM (Qwen3-4B via llama-cpp), and displays a live color-coded transcript. Built with PySide6 (Qt) and Python 3.10+.

**Tech stack**: PySide6, sounddevice, pyaudiowpatch (Windows), faster-whisper, llama-cpp-python, huggingface-hub, NumPy.

## Directory Structure

```
src/bite_size_notes/
├── __init__.py                  # Package root, declares __version__
├── __main__.py                  # `python -m bite_size_notes` entry point
├── app.py                       # main() bootstrap, QApplication, crash handler
├── assets/
│   ├── logo.ico                 # App icon (runtime & PyInstaller)
│   └── readme.png               # Screenshot for README
│
├── audio/                       # Audio capture subsystem
│   ├── __init__.py
│   ├── capture.py               # AudioCaptureThread, AudioChunk
│   ├── devices.py               # Device enumeration (mic, loopback)
│   └── mixer.py                 # mix_audio() utility
│
├── gui/                         # Qt user interface
│   ├── __init__.py
│   ├── main_window.py           # MainWindow, _ModelPreloadThread, _SummarizeThread
│   ├── transcript_view.py       # TranscriptView (center panel)
│   ├── chat_bubble.py           # TranscriptLineWidget, _AutoResizePlainTextEdit
│   ├── sidebar_panel.py         # SidebarPanel, _SessionItemWidget
│   ├── output_panel.py          # OutputPanel (summary display)
│   ├── notes_panel.py           # NotesPanel (floating overlay)
│   ├── settings_dialog.py       # SettingsDialog, model download threads
│   ├── export_dialog.py         # export_transcript(), export_output()
│   └── themes.py                # Dark/Light palettes, stylesheet builder
│
├── models/                      # Data models & persistence
│   ├── __init__.py
│   ├── transcript.py            # TranscriptSegment, TranscriptSession
│   └── session_store.py         # SessionStore (filesystem persistence)
│
├── summarization/               # LLM summarization
│   ├── __init__.py
│   └── engine.py                # Qwen3-4B GGUF via llama-cpp-python
│
├── transcription/               # Speech-to-text
│   ├── __init__.py
│   ├── engine.py                # TranscriptionEngine (faster-whisper wrapper)
│   ├── worker.py                # TranscriberWorker (QThread)
│   └── model_utils.py           # Model cache checks & downloads
│
└── utils/                       # Shared utilities
    ├── __init__.py
    ├── config.py                # AppConfig (QSettings wrapper)
    └── platform.py              # is_windows(), is_macos()
```

## Module Responsibilities

### `audio/`

Handles all audio input. `AudioCaptureThread` opens two parallel streams — one for the microphone (via sounddevice) and one for system/loopback audio (WASAPI on Windows, BlackHole on macOS). It accumulates audio in per-stream buffers, runs silence detection, and flushes `AudioChunk` dataclass objects into a shared `queue.Queue`. `devices.py` provides device enumeration and auto-detection helpers. `mixer.py` contains a utility for mixing two audio arrays (zero-pad + normalize).

### `transcription/`

Converts audio chunks to text. `TranscriptionEngine` wraps `faster_whisper.WhisperModel` and runs inference with VAD filtering. `TranscriberWorker` is a `QThread` that pulls `AudioChunk` objects from the shared queue, calls the engine, and emits `transcription_ready` Qt signals with speaker label, timestamp, and text. `model_utils.py` provides helpers to check if a Whisper model is cached and to download one.

### `summarization/`

Generates meeting summaries from transcript text. Uses the Qwen3-4B-Q4_K_M GGUF model via `llama-cpp-python`. The module provides `load_summarizer()` to download/load the model and `summarize()` to run inference with a structured system prompt that produces formatted meeting notes.

### `gui/`

All Qt UI code. `MainWindow` orchestrates the application — managing the record/stop lifecycle, connecting signals between audio/transcription threads and the UI, and handling session management. The layout is a horizontal `QSplitter` with three panels: `SidebarPanel` (session list), `TranscriptView` (live transcript with editable chat bubbles), and `OutputPanel` (summary display). `NotesPanel` is a floating overlay for user notes. `SettingsDialog` manages preferences and model downloads. `themes.py` provides dark/light/system theme support.

### `models/`

Data structures and persistence. `TranscriptSegment` represents a single transcribed utterance (text, source, timestamp, speaker). `TranscriptSession` aggregates segments into a session with title, summary, and export methods (text, SRT, Markdown, JSON). `SessionStore` manages reading/writing session JSON files to the OS-specific app data directory.

### `utils/`

Shared configuration and platform detection. `AppConfig` wraps `QSettings` with typed properties for all user preferences (devices, model size, language, theme). `platform.py` provides `is_windows()` and `is_macos()` helpers used throughout the codebase.

## Class Hierarchy

### Audio

| Class | Base | Role |
|---|---|---|
| `AudioChunk` | `dataclass` | Data container: `data` (float32 ndarray), `source` ("mic"/"loopback"), `timestamp`, `sample_rate` |
| `AudioCaptureThread` | `threading.Thread` | Opens mic + loopback streams, silence detection, flushes chunks to queue |
| `AudioDevice` | `dataclass` | Device descriptor: `index`, `name`, `max_input_channels`, `default_samplerate`, `is_loopback` |

### Transcription

| Class | Base | Role |
|---|---|---|
| `TranscriptionEngine` | — | Wraps `faster_whisper.WhisperModel`; `transcribe(audio) -> list[dict]` |
| `TranscriberWorker` | `QThread` | Pulls chunks from queue, runs engine, emits `transcription_ready` signal |

### Summarization

| Function | Role |
|---|---|
| `load_summarizer()` | Downloads/loads Qwen3-4B GGUF, returns `Llama` instance |
| `summarize(llm, text)` | Runs chat completion, strips think blocks, returns summary string |
| `is_summarizer_cached()` | Checks HF cache for the GGUF file |
| `download_summarizer_sync()` | Downloads the GGUF via `hf_hub_download` |

### GUI

| Class | Base | Role |
|---|---|---|
| `MainWindow` | `QMainWindow` | Top-level window; orchestrates recording, transcription, summarization, sessions |
| `TranscriptView` | `QWidget` | Scrollable list of transcript chat bubbles |
| `TranscriptLineWidget` | `QFrame` | Single transcript entry: timestamp + speaker label + editable text |
| `_AutoResizePlainTextEdit` | `QPlainTextEdit` | Text edit that auto-sizes to content height |
| `SidebarPanel` | `QWidget` | Session list with new/rename/delete actions |
| `_SessionItemWidget` | `QWidget` | Single session row in the sidebar |
| `OutputPanel` | `QWidget` | Summary display with "Bite Size It" button, copy/export controls |
| `NotesPanel` | `QFrame` | Floating 300x250 overlay for user notes |
| `SettingsDialog` | `QDialog` | Preferences: theme, devices, model size, language, summarizer |
| `_ModelPreloadThread` | `QThread` | Loads `TranscriptionEngine` in background at startup |
| `_SummarizeThread` | `QThread` | Runs summarization in background |
| `_ModelDownloadThread` | `QThread` | Downloads Whisper model (from settings dialog) |
| `_SummarizerDownloadThread` | `QThread` | Downloads GGUF model (from settings dialog) |

### Models

| Class | Base | Role |
|---|---|---|
| `TranscriptSegment` | `dataclass` | Single utterance: `text`, `source`, `timestamp`, `speaker_label` |
| `TranscriptSession` | `dataclass` | Full session: segments list, title, summary, start_time, UUID; export methods |
| `SessionStore` | — | Filesystem CRUD for session JSON files in app data directory |

### Utils

| Class | Base | Role |
|---|---|---|
| `AppConfig` | — | `QSettings` wrapper with typed properties for all user preferences |

---

See also: [Data Flow](data-flow.md) | [Platform Guide](platform-guide.md)
