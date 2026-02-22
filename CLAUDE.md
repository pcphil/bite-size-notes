# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bite-Size Notes is a desktop meeting transcriber that captures microphone and system audio simultaneously, runs local Whisper speech-to-text (via faster-whisper), and displays a live color-coded transcript. Built with PySide6 (Qt) and Python 3.10+.

## Commands

```bash
# Install dependencies (uses uv with hatch build backend)
uv sync

# Install with dev dependencies
uv sync --extra dev

# Run the application
uv run bite-size-notes
# or
uv run python -m bite_size_notes

# Run tests
uv run pytest

# Run a single test
uv run pytest tests/test_foo.py::test_bar -v

# Lint and format
uv run ruff check src/
uv run ruff format src/
```

## Architecture

### Data Flow

Audio capture → Queue → Transcription worker → Qt signals → GUI

1. **AudioCaptureThread** (`audio/capture.py`) — a `threading.Thread` that opens two parallel audio streams (mic via sounddevice, system/loopback via WASAPI on Windows or BlackHole on macOS). Accumulates audio in buffers and flushes `AudioChunk` objects to a shared `queue.Queue` every N seconds.
2. **TranscriberWorker** (`transcription/worker.py`) — a `QThread` that pulls `AudioChunk`s from the queue, runs them through `TranscriptionEngine`, and emits `transcription_ready(speaker, timestamp, text)` Qt signals.
3. **TranscriptionEngine** (`transcription/engine.py`) — thin wrapper around `faster_whisper.WhisperModel`. All audio is float32, 16 kHz, mono.
4. **MainWindow** (`gui/main_window.py`) — connects signals, manages record/stop lifecycle, updates the `TranscriptView`.

### Key Design Patterns

- **Dual-stream capture**: Mic and loopback are separate streams with independent buffers/locks. On Windows, loopback uses pyaudiowpatch (WASAPI) in its own thread with resampling to 16 kHz. On macOS, BlackHole is treated as a regular sounddevice input.
- **Thread communication**: Audio threads → `queue.Queue` → QThread worker → Qt signals → GUI. The queue has a max size of 100; oldest chunks are dropped when full.
- **Settings persistence**: `AppConfig` (`utils/config.py`) wraps `QSettings` with typed properties. Device index `-1` means "use default / auto-detect".

### Platform Differences

- **Windows**: System audio captured via `pyaudiowpatch` (WASAPI loopback). This dependency is conditional (`sys_platform == 'win32'` in pyproject.toml).
- **macOS**: System audio requires BlackHole virtual audio driver installed separately. Captured as a regular sounddevice input.

### Export Formats

`TranscriptSession` (`models/transcript.py`) supports export to plain text, SRT subtitles, Markdown, and JSON.
