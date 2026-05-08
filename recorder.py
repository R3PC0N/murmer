import json
import subprocess
import sys
import threading

import numpy as np
import sounddevice as sd

import config

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _query_input_names() -> list[str]:
    """Return names of all input devices.

    On Windows uses a subprocess to avoid a WASAPI/COM deadlock that occurs
    under pythonw.exe when sd.query_devices() is called from a thread that
    shares a process with WebView2's COM apartment.
    """
    if sys.platform != "win32":
        seen: set[str] = set()
        names: list[str] = []
        for dev in sd.query_devices():
            if dev["max_input_channels"] > 0 and dev["name"] not in seen:
                seen.add(dev["name"])
                names.append(dev["name"])
        return names
    try:
        result = subprocess.run(
            [sys.executable, "-c",
             "import sounddevice as sd, json; seen=set(); out=[];\n"
             "[out.append(d['name']) or seen.add(d['name'])\n"
             " for d in sd.query_devices()\n"
             " if d['max_input_channels']>0 and d['name'] not in seen];\n"
             "print(json.dumps(out))"],
            capture_output=True, text=True, timeout=8,
            creationflags=_NO_WINDOW,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except Exception:
        pass
    return []


def list_input_devices() -> list[tuple[int, str]]:
    """Return (index, name) pairs for all available input devices, deduplicated."""
    names = _query_input_names()
    return list(enumerate(names))


def get_device_names() -> list[str]:
    """Return display names for the settings dropdown (includes a default option)."""
    return ["Default"] + _query_input_names()


def resolve_device(name: str | None) -> int | None:
    """Resolve a device name to its sounddevice index, or None for system default."""
    if not name or name == "Default":
        return None
    for idx, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0 and dev["name"] == name:
            return idx
    return None


def device_available(name: str | None) -> bool:
    """Return True if the configured device exists (or Default is used)."""
    names = _query_input_names()
    if not name or name == "Default":
        return len(names) > 0
    return name in names


def check_device(name: str | None) -> dict:
    """Return {"found": bool, "name": str} for splash/log feedback."""
    names = _query_input_names()
    if not name or name == "Default":
        if names:
            return {"found": True, "name": names[0]}
        return {"found": False, "name": "Default"}
    if name in names:
        return {"found": True, "name": name}
    return {"found": False, "name": name}


class Recorder:
    def __init__(self):
        self._frames = []
        self._recording = False
        self._stream = None
        self._lock = threading.Lock()

    def start(self):
        self._frames = []
        self._recording = True
        device = resolve_device(config.AUDIO_DEVICE)
        self._stream = sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=1024,
            device=device,
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, indata, frames, time_info, status):
        with self._lock:
            if self._recording:
                self._frames.append(indata.copy())

    def stop(self) -> np.ndarray | None:
        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if self._frames:
                return np.concatenate(self._frames, axis=0).flatten()
            return None
