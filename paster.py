import os
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping


class TextInsertionError(RuntimeError):
    """Raised when text could not be inserted into the focused application."""


def detect_backend(
    platform: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Select the text insertion backend for the current desktop session."""
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ

    if platform == "win32":
        return "windows"
    if platform.startswith("linux"):
        session_type = environ.get("XDG_SESSION_TYPE", "").lower()
        if session_type == "wayland" or environ.get("WAYLAND_DISPLAY"):
            return "wayland"
        if session_type == "x11" or environ.get("DISPLAY"):
            return "x11"
        raise TextInsertionError(
            "Cannot determine the Linux display session; expected "
            "XDG_SESSION_TYPE, WAYLAND_DISPLAY, or DISPLAY."
        )
    raise TextInsertionError(f"Text insertion is unsupported on platform {platform!r}.")


def _require_executable(name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        raise TextInsertionError(
            f"The {name!r} executable is required for text insertion but was not found."
        )
    return executable


def _run_text_command(command: list[str], stdin_text: str | None, backend: str):
    try:
        result = subprocess.run(
            command,
            input=stdin_text,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise TextInsertionError(f"{backend} text insertion could not start: {exc}") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no error details"
        raise TextInsertionError(
            f"{backend} text insertion failed with exit code {result.returncode}: {detail}"
        )


def _paste_windows(text: str):
    try:
        import keyboard
        import pyperclip
    except ImportError as exc:
        raise TextInsertionError(f"Windows text insertion dependency is missing: {exc}") from exc

    previous = None
    try:
        previous = pyperclip.paste()
        pyperclip.copy(text)
        time.sleep(0.05)
        keyboard.send("ctrl+v")
        time.sleep(0.1)
    except Exception as exc:
        raise TextInsertionError(f"Windows text insertion failed: {exc}") from exc
    finally:
        if previous is not None:
            try:
                pyperclip.copy(previous)
            except Exception:
                pass


def _paste_x11(text: str):
    # xdotool types directly, including in terminals where Ctrl+V is not paste.
    xdotool = _require_executable("xdotool")
    _run_text_command(
        [xdotool, "type", "--clearmodifiers", "--delay", "0", "--", text],
        None,
        "X11",
    )


def _paste_wayland(text: str):
    # wtype defaults to no delay, which can make compositors or applications
    # drop rapid key events (especially shifted punctuation). Stdin keeps text
    # literal and avoids command-line length limits. Tabs are normalized because
    # a real Tab key commonly changes focus instead of inserting indentation.
    wtype = _require_executable("wtype")
    literal_text = text.replace("\t", "    ")
    _run_text_command([wtype, "-d", "5", "-"], literal_text, "Wayland")


def paste_text(text: str):
    backend = detect_backend()
    if backend == "windows":
        _paste_windows(text)
    elif backend == "wayland":
        _paste_wayland(text)
    else:
        _paste_x11(text)
