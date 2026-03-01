# Contributing to Bite-Size Notes

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- Windows 10+ (for system audio capture via WASAPI loopback)
  - macOS is supported but requires [BlackHole](https://existential.audio/blackhole/) for system audio

## Getting Started

```bash
# Clone the repo
git clone https://github.com/pcphil/bite-size-notes.git
cd bite-size-notes

# Install all dependencies (including dev tools)
uv sync --extra dev

# Run the application
uv run bite-size-notes
```

## Development Workflow

### Running the App

```bash
uv run bite-size-notes
# or
uv run python -m bite_size_notes
```

### Tests

```bash
# Run all tests
uv run pytest

# Run a specific test
uv run pytest tests/test_foo.py::test_bar -v
```

### Linting & Formatting

```bash
# Check for lint issues
uv run ruff check src/

# Auto-format code
uv run ruff format src/
```

Please run both lint and format before submitting a PR.

## Architecture Overview

```
Audio capture → Queue → Transcription worker → Qt signals → GUI
```

- **AudioCaptureThread** (`audio/capture.py`) — Opens mic + system loopback streams in parallel threads. Flushes `AudioChunk` objects to a shared `queue.Queue`.
- **TranscriberWorker** (`transcription/worker.py`) — `QThread` that pulls chunks from the queue, runs Whisper inference, and emits Qt signals.
- **TranscriptionEngine** (`transcription/engine.py`) — Wrapper around `faster_whisper.WhisperModel`. Expects float32, 16 kHz, mono audio.
- **MainWindow** (`gui/main_window.py`) — Connects signals, manages record/stop lifecycle, displays the transcript.
- **AppConfig** (`utils/config.py`) — Settings persistence via `QSettings`.

### Key Conventions

- Thread communication uses `queue.Queue` (audio threads to QThread) and Qt signals (QThread to GUI). Never call GUI methods from non-Qt threads.
- Audio is always float32, 16 kHz, mono internally.
- Device index `-1` means "use default / auto-detect".
- The queue has a max size of 100; oldest chunks are dropped when full.

### Platform-Specific Code

- **Windows**: System audio via `pyaudiowpatch` (WASAPI loopback). This dependency is conditional in `pyproject.toml`.
- **macOS**: System audio via BlackHole, captured as a regular `sounddevice` input.

## Building Executables

Requires the `dev` extra (`pyinstaller` is included):

```bash
# Build the exe
uv run python build_exe.py

# Build a debug exe (opens a console window for troubleshooting)
uv run python build_exe.py --debug

# Build the exe + Inno Setup installer (requires iscc on PATH)
uv run python build_exe.py --installer
```

Output lands in `dist/bite_size_notes/`. The Inno Setup installer outputs to `dist/BiteSizeNotes_Setup.exe`.

### Debugging a Frozen Build

Use `--debug` to build with a visible console window. If the app crashes on startup, the console stays open and displays the full traceback. Press Enter to dismiss it. A `crash.log` file is also written to `%APPDATA%/Bite-Size Notes/`.

## Submitting Changes

1. Fork the repo and create a feature branch from `main`.
2. Make your changes in small, focused commits.
3. Ensure `uv run ruff check src/` and `uv run pytest` pass.
4. Open a pull request against `main` with a clear description of what changed and why.
