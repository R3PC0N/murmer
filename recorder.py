import json
import subprocess
import sys
import threading
from pathlib import Path

import numpy as np
import sounddevice as sd

import config

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


_DEVICE_QUERY_SCRIPT = (
    "import sounddevice as sd, json; seen=set(); out=[];"
    "[out.append(d['name']) or seen.add(d['name'])"
    " for d in sd.query_devices()"
    " if d['max_input_channels']>0 and d['name'] not in seen];"
    "print(json.dumps(out))"
)


def _query_input_names() -> list[str]:
    """Return names of all input devices.

    On Windows, sd.query_devices() deadlocks under pythonw.exe due to a
    WASAPI/COM conflict with WebView2. Fix: run the query in a fresh
    python.exe subprocess (console subsystem, no COM conflict).
    """
    if sys.platform != "win32":
        seen: set[str] = set()
        names: list[str] = []
        for dev in sd.query_devices():
            if dev["max_input_channels"] > 0 and dev["name"] not in seen:
                seen.add(dev["name"])
                names.append(dev["name"])
        return names

    # Use python.exe (console), never pythonw.exe — the latter shares the
    # same WASAPI/COM hang under pythonw.exe parent processes.
    python_exe = Path(sys.executable).with_name("python.exe")
    if not python_exe.exists():
        python_exe = Path(sys.executable)

    try:
        proc = subprocess.Popen(
            [str(python_exe), "-c", _DEVICE_QUERY_SCRIPT],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=_NO_WINDOW,
        )
        try:
            stdout, _ = proc.communicate(timeout=8)
            data = stdout.decode("utf-8", errors="ignore").strip()
            if data:
                return json.loads(data)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
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
