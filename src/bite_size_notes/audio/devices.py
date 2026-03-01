"""Audio device enumeration with platform-specific loopback support."""

import logging
from dataclasses import dataclass

import sounddevice as sd

from bite_size_notes.utils.platform import is_macos, is_windows

logger = logging.getLogger(__name__)


@dataclass
class AudioDevice:
    index: int
    name: str
    max_input_channels: int
    default_samplerate: float
    is_loopback: bool = False


def list_input_devices() -> list[AudioDevice]:
    """Return all input (microphone) devices."""
    devices = []
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            devices.append(
                AudioDevice(
                    index=i,
                    name=d["name"],
                    max_input_channels=d["max_input_channels"],
                    default_samplerate=d["default_samplerate"],
                )
            )
    logger.info("Found %d input devices", len(devices))
    return devices


def get_default_mic() -> AudioDevice | None:
    """Return the system default input device."""
    try:
        info = sd.query_devices(kind="input")
        idx = sd.default.device[0]
        device = AudioDevice(
            index=idx,
            name=info["name"],
            max_input_channels=info["max_input_channels"],
            default_samplerate=info["default_samplerate"],
        )
        logger.info("Default mic: %s (index %d)", device.name, device.index)
        return device
    except Exception:
        logger.warning("No default mic found")
        return None


def get_loopback_device() -> AudioDevice | None:
    """Find a loopback/system audio capture device.

    Windows: Uses pyaudiowpatch to find WASAPI loopback devices.
    macOS: Looks for BlackHole in sounddevice input devices.
    """
    if is_windows():
        return _get_wasapi_loopback()
    elif is_macos():
        return _get_blackhole_device()
    return None


def _get_wasapi_loopback() -> AudioDevice | None:
    """Find the default WASAPI loopback device on Windows."""
    try:
        import pyaudiowpatch as pyaudio

        p = pyaudio.PyAudio()
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_speakers = p.get_device_info_by_index(
            wasapi_info["defaultOutputDevice"]
        )

        # Find the loopback device corresponding to the default speakers
        for i in range(p.get_device_count()):
            device = p.get_device_info_by_index(i)
            if (
                device.get("isLoopbackDevice", False)
                and device["name"].startswith(default_speakers["name"].split(" (")[0])
            ):
                result = AudioDevice(
                    index=i,
                    name=device["name"],
                    max_input_channels=device["maxInputChannels"],
                    default_samplerate=device["defaultSampleRate"],
                    is_loopback=True,
                )
                p.terminate()
                return result

        # Fallback: return any loopback device
        for i in range(p.get_device_count()):
            device = p.get_device_info_by_index(i)
            if device.get("isLoopbackDevice", False):
                result = AudioDevice(
                    index=i,
                    name=device["name"],
                    max_input_channels=device["maxInputChannels"],
                    default_samplerate=device["defaultSampleRate"],
                    is_loopback=True,
                )
                p.terminate()
                return result

        p.terminate()
    except Exception:
        pass
    return None


def _get_blackhole_device() -> AudioDevice | None:
    """Find BlackHole virtual audio device on macOS."""
    for i, d in enumerate(sd.query_devices()):
        if "blackhole" in d["name"].lower() and d["max_input_channels"] > 0:
            return AudioDevice(
                index=i,
                name=d["name"],
                max_input_channels=d["max_input_channels"],
                default_samplerate=d["default_samplerate"],
                is_loopback=True,
            )
    return None


def list_loopback_devices() -> list[AudioDevice]:
    """List all available loopback devices (Windows only, for device selection)."""
    devices = []
    if is_windows():
        try:
            import pyaudiowpatch as pyaudio

            p = pyaudio.PyAudio()
            for i in range(p.get_device_count()):
                device = p.get_device_info_by_index(i)
                if device.get("isLoopbackDevice", False):
                    devices.append(
                        AudioDevice(
                            index=i,
                            name=device["name"],
                            max_input_channels=device["maxInputChannels"],
                            default_samplerate=device["defaultSampleRate"],
                            is_loopback=True,
                        )
                    )
            p.terminate()
        except Exception:
            pass
    elif is_macos():
        for i, d in enumerate(sd.query_devices()):
            if "blackhole" in d["name"].lower() and d["max_input_channels"] > 0:
                devices.append(
                    AudioDevice(
                        index=i,
                        name=d["name"],
                        max_input_channels=d["max_input_channels"],
                        default_samplerate=d["default_samplerate"],
                        is_loopback=True,
                    )
                )
    return devices
