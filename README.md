<p align="center">
  <img src="src/bite_size_notes/assets/readme.png" alt="Bite-Size Notes" width="800"/>
</p>

A desktop meeting transcriber that captures your microphone and system audio simultaneously, runs local Whisper speech-to-text, and displays a live color-coded transcript.

- **Local & private** — all transcription runs on your machine via [faster-whisper](https://github.com/SYSTRAN/faster-whisper), no audio leaves your device
- **Dual-stream capture** — records your mic ("Me") and system/speaker audio ("Others") separately so you can tell who said what
- **Live transcript** — color-coded, timestamped text appears in real time as you record
- **Export** — save transcripts as plain text, SRT subtitles, Markdown, or JSON

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- **Windows**: system audio capture works out of the box (WASAPI loopback)
- **macOS**: install [BlackHole](https://github.com/ExistentialAudio/BlackHole) to capture system audio

## Installation

```bash
git clone https://github.com/<your-username>/bite-size-notes.git
cd bite-size-notes
uv sync
```

## Usage

```bash
uv run bite-size-notes
```

1. Click **Record** (or `Ctrl+R`) to start capturing audio
2. The transcript appears live in the main window
3. Click **Stop** to end the recording
4. Click the **📥 Export** button in the output panel to save the transcript

### Settings

Open **Settings** (`Ctrl+,`) to configure:

- **Microphone** and **system audio (loopback)** devices
- **Whisper model size** — tiny, base, small, or medium (larger = more accurate but slower)
- **Language** — English, Spanish, French, German, Chinese, Japanese, Korean, Portuguese, or auto-detect
- **Chunk duration** — how many seconds of audio to buffer before transcribing (3–30s)

## Building

```bash
# Build a standalone exe (requires dev dependencies)
uv sync --extra dev
uv run python build_exe.py

# Build a debug exe (console stays open on crash for troubleshooting)
uv run python build_exe.py --debug
```

## Development

```bash
# Install with dev dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Lint and format
uv run ruff check src/
uv run ruff format src/
```

## License

MIT
