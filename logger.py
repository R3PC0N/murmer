import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Levels:
#   DEBUG       — system messages (loading, settings, hotkey, etc.)
#   RESULT      — final transcription output (shown in compact mode, saved to history)
#   ERROR       — errors (shown in all modes)

if sys.platform == "win32":
    _LOG_DIR = Path(os.getenv("LOCALAPPDATA", Path.home())) / "Murmur"
else:
    _LOG_DIR = Path.home() / ".local" / "share" / "Murmur"

_HISTORY_FILE = _LOG_DIR / "history.log"
_STARTUP_LOG   = _LOG_DIR / "startup.log"
_startup_fresh  = True  # overwrite on first write each run
_buffer: list[tuple[str, str, str]] = []  # (timestamp, level, message)
_callbacks: list = []


def log(message: str, level: str = "DEBUG"):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = (ts, level, message)
    _buffer.append(entry)
    print(message)
    for cb in list(_callbacks):
        try:
            cb(entry)
        except Exception:
            pass
    if level == "RESULT":
        _write_history(ts, message)


def _write_history(ts: str, message: str):
    try:
        _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        date = datetime.now().strftime("%Y-%m-%d")
        with open(_HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{date} {ts}] {message}\n")
    except Exception:
        pass


def get_buffer() -> list[tuple[str, str, str]]:
    return list(_buffer)


def clear_buffer():
    _buffer.clear()


def add_callback(cb):
    if cb not in _callbacks:
        _callbacks.append(cb)


def remove_callback(cb):
    if cb in _callbacks:
        _callbacks.remove(cb)


def open_history():
    if sys.platform == "win32":
        if _HISTORY_FILE.exists():
            subprocess.Popen(["notepad.exe", str(_HISTORY_FILE)])
        else:
            subprocess.Popen(["notepad.exe"])
    else:
        if _HISTORY_FILE.exists():
            subprocess.Popen(["xdg-open", str(_HISTORY_FILE)])
        else:
            subprocess.Popen(["xdg-open", str(_HISTORY_FILE.parent)])


def log_startup(msg: str):
    global _startup_fresh
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        mode = "w" if _startup_fresh else "a"
        _startup_fresh = False
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        with open(_STARTUP_LOG, mode, encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def open_startup_log():
    if sys.platform == "win32":
        if _STARTUP_LOG.exists():
            subprocess.Popen(["notepad.exe", str(_STARTUP_LOG)])
        else:
            subprocess.Popen(["notepad.exe"])
    else:
        if _STARTUP_LOG.exists():
            subprocess.Popen(["xdg-open", str(_STARTUP_LOG)])
        else:
            subprocess.Popen(["xdg-open", str(_LOG_DIR)])
