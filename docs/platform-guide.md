# Platform-Specific Behavior

This document covers platform differences in audio capture, configuration, and export formats.

See also: [Architecture Overview](architecture.md) | [Data Flow](data-flow.md)

## Windows — WASAPI Loopback

### How It Works

System audio on Windows is captured via WASAPI loopback using the `pyaudiowpatch` package (a conditional dependency: `pyaudiowpatch>=0.2.12; sys_platform == 'win32'`).

The capture runs in a dedicated daemon thread inside `AudioCaptureThread`:

1. `_start_wasapi_loopback()` opens a blocking `pyaudio` stream on the detected loopback device
2. Reads `BLOCK_SIZE` (1024) frames at a time in a tight loop
3. Multi-channel audio is reshaped and averaged to mono
4. If the device's native sample rate differs from 16 kHz, audio is resampled via `np.interp` (linear interpolation)
5. Resulting float32 samples are appended to `_loopback_buffer` under `_loopback_lock`
6. The thread exits when `_wasapi_stop_event` is set

### Device Detection

`devices._get_wasapi_loopback()` (`audio/devices.py`):

1. Instantiates `pyaudio.PyAudio()`
2. Finds the WASAPI host API info
3. Gets the default output (speaker) device
4. Searches for a loopback device whose name starts with the speaker's name prefix
5. Falls back to any available loopback device

`devices.list_loopback_devices()` enumerates all devices with `isLoopbackDevice == True` for display in the Settings dialog.

### Session Storage Path

```
%LOCALAPPDATA%\pcphil\Bite-Size-Notes\sessions\
```

Legacy migration moves files from `%LOCALAPPDATA%\BiteSize\Bite-Size-Notes\sessions\`.

## macOS — BlackHole

### How It Works

System audio on macOS requires the [BlackHole](https://existential.audio/blackhole/) virtual audio driver, installed separately by the user. Once installed, BlackHole appears as a standard audio input device and is captured via `sounddevice.InputStream` — no platform-specific code path is needed for the actual capture.

### Device Detection

`devices._get_blackhole_device()` (`audio/devices.py`):

1. Queries all devices via `sounddevice.query_devices()`
2. Searches for any device with `"blackhole"` (case-insensitive) in its name
3. Verifies the device has input channels

If no BlackHole device is found when recording starts, `MainWindow._start_recording()` shows a warning dialog informing the user to install BlackHole.

### Setup Instructions

1. Download BlackHole from [existential.audio/blackhole](https://existential.audio/blackhole/)
2. Install the package (BlackHole 2ch is sufficient)
3. Open **Audio MIDI Setup** (in `/Applications/Utilities/`)
4. Create a **Multi-Output Device** that includes both your speakers and BlackHole
5. Set the Multi-Output Device as your system output
6. In Bite-Size Notes settings, the BlackHole device should appear automatically in the loopback device dropdown

### Session Storage Path

```
~/Library/Application Support/pcphil/Bite-Size-Notes/sessions/
```

Legacy migration moves files from `~/Library/Application Support/BiteSize/Bite-Size-Notes/sessions/`.

## Configuration

### AppConfig

`AppConfig` (`utils/config.py`) wraps `QSettings("pcphil", "Bite-Size-Notes")` with typed Python properties.

| Property | QSettings Key | Default | Description |
|---|---|---|---|
| `mic_device` | `audio/mic_device` | `-1` | Mic device index (`-1` = auto-detect) |
| `loopback_device` | `audio/loopback_device` | `-1` | Loopback device index (`-1` = auto-detect) |
| `model_size` | `transcription/model_size` | `"base"` | Whisper model size (`tiny`, `base`, `small`, `medium`) |
| `language` | `transcription/language` | `"en"` | Transcription language code or `None` for auto-detect |
| `theme` | `appearance/theme` | `"dark"` | UI theme (`dark`, `light`, `system`) |
| `summarizer_model` | `summarization/model` | `"Qwen3-4B-Q4_K_M"` | Summarizer model identifier |

### QSettings Backend

- **Windows**: Windows Registry (`HKEY_CURRENT_USER\Software\pcphil\Bite-Size-Notes`)
- **macOS**: Plist file (`~/Library/Preferences/pcphil.Bite-Size-Notes.plist`)

### Device Resolution (`-1` = Auto-Detect)

When a device index is `-1`, the app resolves it at recording time:

- **Mic**: `get_default_mic()` → calls `sounddevice.query_devices(kind='input')` to find the system default input device
- **Loopback**: `get_loopback_device()` → dispatches to `_get_wasapi_loopback()` on Windows or `_get_blackhole_device()` on macOS

Users can override auto-detection by selecting a specific device in the Settings dialog, which stores its numeric index.

### Settings Migration

On first run, both `AppConfig` and `SessionStore` check for data from the legacy organization name (`"BiteSize"`) and migrate it to the current organization (`"pcphil"`). This is a one-time operation:

- `AppConfig._migrate_from_old_org()` copies QSettings keys
- `SessionStore._migrate_from_old_org()` moves session JSON files

## Export Formats

All export methods are on `TranscriptSession` (`models/transcript.py`). The `export_transcript()` function in `gui/export_dialog.py` shows a save dialog and dispatches to the appropriate method based on the selected file filter.

### Plain Text (`.txt`)

```
[00:00] Me: Hello everyone, let's get started.
[00:05] Others: Sounds good.
[00:12] Me: First item on the agenda...
```

One line per segment: `[MM:SS] Speaker: text`, joined by newlines. Generated by `TranscriptSession.to_text()`.

### SRT Subtitles (`.srt`)

```
1
00:00:00,000 --> 00:00:05,000
Me: Hello everyone, let's get started.

2
00:00:05,000 --> 00:00:12,000
Others: Sounds good.
```

Standard SRT format with sequential index, timecodes (`HH:MM:SS,mmm`), and `Speaker: text`. End time is the next segment's timestamp, or start + 5 seconds for the last segment. Generated by `TranscriptSession.to_srt()`.

### Markdown (`.md`)

```markdown
# Meeting — 2026-02-28 14:30

**2026-02-28 14:30**

---

**[00:00] Me**: Hello everyone, let's get started.

**[00:05] Others**: Sounds good.
```

H1 title, bold date, horizontal rule, then each segment with bold timestamp/speaker and plain text body. Blank lines between entries. Generated by `TranscriptSession.to_markdown()`.

### JSON (`.json`)

Full session data in the same schema as the session storage files (see [Data Flow — Session File Format](data-flow.md#session-file-format)), with 2-space indentation. Generated by `TranscriptSession.to_json()` via `TranscriptSession.to_dict()`.

### Output Export

The summarization output (in the `OutputPanel`) can be exported separately via `export_output()` as a plain text `.txt` file.

---

See also: [Architecture Overview](architecture.md) | [Data Flow](data-flow.md)
