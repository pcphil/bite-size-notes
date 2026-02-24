"""Audio capture thread with dual-stream mic + loopback support."""

import queue
import threading
import time
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

from bite_size_notes.utils.platform import is_windows


@dataclass
class AudioChunk:
    """A chunk of captured audio data."""

    data: np.ndarray  # float32, mono, 16kHz
    source: str  # "mic" or "loopback"
    timestamp: float  # seconds since recording started
    sample_rate: int = 16000


class AudioCaptureThread(threading.Thread):
    """Captures audio from microphone and system loopback simultaneously.

    Mic audio is captured via sounddevice on all platforms.
    Loopback audio is captured via pyaudiowpatch (WASAPI) on Windows,
    or via sounddevice (BlackHole) on macOS.

    Audio chunks are pushed to the output queue every `chunk_seconds`.
    """

    SAMPLE_RATE = 16000
    CHANNELS = 1
    BLOCK_SIZE = 1024  # frames per callback

    def __init__(
        self,
        mic_device_index: int,
        loopback_device_index: int | None,
        audio_queue: queue.Queue,
        chunk_seconds: float = 5.0,
    ):
        super().__init__(daemon=True)
        self.mic_device_index = mic_device_index
        self.loopback_device_index = loopback_device_index
        self.audio_queue = audio_queue
        self.chunk_seconds = chunk_seconds
        self._stop_event = threading.Event()
        self._start_time = 0.0

        # Buffers protected by locks
        self._mic_buffer: list[np.ndarray] = []
        self._mic_lock = threading.Lock()
        self._loopback_buffer: list[np.ndarray] = []
        self._loopback_lock = threading.Lock()

        # RMS levels for UI meters (updated per callback)
        self.mic_rms: float = 0.0
        self.loopback_rms: float = 0.0

    def run(self):
        self._start_time = time.monotonic()
        streams = []

        # --- Mic stream (sounddevice on all platforms) ---
        try:
            mic_stream = sd.InputStream(
                device=self.mic_device_index,
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                dtype="float32",
                blocksize=self.BLOCK_SIZE,
                callback=self._mic_callback,
            )
            mic_stream.start()
            streams.append(mic_stream)
        except Exception as e:
            self._push_error(f"Mic stream error: {e}")
            return

        # --- Loopback stream ---
        if self.loopback_device_index is not None:
            try:
                if is_windows():
                    self._start_wasapi_loopback(streams)
                else:
                    # macOS: BlackHole appears as a regular input device
                    loopback_stream = sd.InputStream(
                        device=self.loopback_device_index,
                        samplerate=self.SAMPLE_RATE,
                        channels=self.CHANNELS,
                        dtype="float32",
                        blocksize=self.BLOCK_SIZE,
                        callback=self._loopback_callback,
                    )
                    loopback_stream.start()
                    streams.append(loopback_stream)
            except Exception as e:
                self._push_error(f"Loopback stream error: {e}")

        # --- Silence-based accumulation loop ---
        SILENCE_THRESHOLD = 0.01  # RMS below this = silence
        SILENCE_DURATION = 0.8  # seconds of silence before flushing
        POLL_INTERVAL = 0.1  # polling interval in seconds

        had_speech = False
        silence_start = None
        last_flush = time.monotonic()

        while not self._stop_event.is_set():
            self._stop_event.wait(POLL_INTERVAL)
            now = time.monotonic()

            # Check if either source has speech
            is_speaking = (
                self.mic_rms > SILENCE_THRESHOLD
                or self.loopback_rms > SILENCE_THRESHOLD
            )

            if is_speaking:
                had_speech = True
                silence_start = None
            elif had_speech and silence_start is None:
                silence_start = now

            elapsed = now - last_flush

            # Flush when: speech ended + silence long enough, or max duration reached
            should_flush = False
            if had_speech and silence_start is not None:
                if (now - silence_start) >= SILENCE_DURATION:
                    should_flush = True
            if elapsed >= self.chunk_seconds:
                should_flush = True

            if not should_flush:
                continue

            # Skip flush if buffer contains only silence
            if not had_speech:
                last_flush = now
                continue

            timestamp = now - self._start_time

            # Flush mic buffer
            with self._mic_lock:
                if self._mic_buffer:
                    mic_data = np.concatenate(self._mic_buffer)
                    self._mic_buffer.clear()
                else:
                    mic_data = None

            # Flush loopback buffer
            with self._loopback_lock:
                if self._loopback_buffer:
                    loopback_data = np.concatenate(self._loopback_buffer)
                    self._loopback_buffer.clear()
                else:
                    loopback_data = None

            # Push chunks to queue
            if mic_data is not None and len(mic_data) > self.SAMPLE_RATE:
                self._safe_put(
                    AudioChunk(
                        data=mic_data,
                        source="mic",
                        timestamp=max(0, timestamp - elapsed),
                    )
                )

            if loopback_data is not None and len(loopback_data) > self.SAMPLE_RATE:
                self._safe_put(
                    AudioChunk(
                        data=loopback_data,
                        source="loopback",
                        timestamp=max(0, timestamp - elapsed),
                    )
                )

            # Reset state
            had_speech = False
            silence_start = None
            last_flush = now

        # Cleanup
        for s in streams:
            try:
                s.stop()
                s.close()
            except Exception:
                pass

        # Stop WASAPI loopback thread if running
        if hasattr(self, "_wasapi_stop_event"):
            self._wasapi_stop_event.set()

    def _mic_callback(self, indata, frames, time_info, status):
        """sounddevice callback for microphone input."""
        audio = indata[:, 0].copy()
        self.mic_rms = float(np.sqrt(np.mean(audio**2)))
        with self._mic_lock:
            self._mic_buffer.append(audio)

    def _loopback_callback(self, indata, frames, time_info, status):
        """sounddevice callback for loopback input (macOS BlackHole)."""
        audio = indata[:, 0].copy()
        self.loopback_rms = float(np.sqrt(np.mean(audio**2)))
        with self._loopback_lock:
            self._loopback_buffer.append(audio)

    def _start_wasapi_loopback(self, streams: list):
        """Start WASAPI loopback capture on Windows using pyaudiowpatch."""
        import pyaudiowpatch as pyaudio

        p = pyaudio.PyAudio()
        device_info = p.get_device_info_by_index(self.loopback_device_index)
        device_rate = int(device_info["defaultSampleRate"])
        device_channels = device_info["maxInputChannels"]

        self._wasapi_stop_event = threading.Event()
        self._pyaudio_instance = p

        def wasapi_thread():
            try:
                stream = p.open(
                    format=pyaudio.paFloat32,
                    channels=device_channels,
                    rate=device_rate,
                    input=True,
                    input_device_index=self.loopback_device_index,
                    frames_per_buffer=self.BLOCK_SIZE,
                )

                while not self._wasapi_stop_event.is_set():
                    try:
                        data = stream.read(self.BLOCK_SIZE, exception_on_overflow=False)
                    except Exception:
                        break
                    audio = np.frombuffer(data, dtype=np.float32)

                    # Convert to mono if multi-channel
                    if device_channels > 1:
                        audio = audio.reshape(-1, device_channels).mean(axis=1)

                    # Resample to 16kHz if needed
                    if device_rate != self.SAMPLE_RATE:
                        ratio = self.SAMPLE_RATE / device_rate
                        new_len = int(len(audio) * ratio)
                        indices = np.linspace(0, len(audio) - 1, new_len)
                        audio = np.interp(indices, np.arange(len(audio)), audio).astype(
                            np.float32
                        )

                    self.loopback_rms = float(np.sqrt(np.mean(audio**2)))
                    with self._loopback_lock:
                        self._loopback_buffer.append(audio)

                stream.stop_stream()
                stream.close()
            except Exception:
                pass
            finally:
                p.terminate()

        t = threading.Thread(target=wasapi_thread, daemon=True)
        t.start()

    def _safe_put(self, chunk: AudioChunk):
        """Put a chunk in the queue, dropping oldest if full."""
        try:
            self.audio_queue.put_nowait(chunk)
        except queue.Full:
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                pass
            self.audio_queue.put_nowait(chunk)

    def _push_error(self, message: str):
        """Push an error message as a special chunk."""
        # Errors are logged but don't stop the thread
        pass

    def stop(self):
        """Signal the capture thread to stop."""
        self._stop_event.set()
