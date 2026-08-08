import os
import shlex
import shutil
import socket
import subprocess
import sys
import threading
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path

import app_paths


class HotkeyError(RuntimeError):
    pass


_MURMUR_DESCRIPTION = "Murmur push-to-talk"
_HYPRLAND_KEYS = tuple(f"f{i}" for i in range(1, 13))


def detect_backend(
    platform: str | None = None,
    environ: Mapping[str, str] | None = None,
    hyprctl_available: bool | None = None,
) -> str:
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ

    if platform == "win32":
        return "windows"
    if not platform.startswith("linux"):
        raise HotkeyError(f"Global hotkeys are unsupported on platform {platform!r}.")

    session_type = environ.get("XDG_SESSION_TYPE", "").lower()
    is_wayland = session_type == "wayland" or bool(environ.get("WAYLAND_DISPLAY"))
    if not is_wayland:
        return "x11"

    desktop = environ.get("XDG_CURRENT_DESKTOP", "").lower().split(":")
    has_hyprctl = shutil.which("hyprctl") is not None if hyprctl_available is None else hyprctl_available
    if "hyprland" in desktop and has_hyprctl:
        return "hyprland"
    return "unsupported-wayland"


def normalize_key(key: str) -> str:
    normalized = key.strip().lower()
    aliases = {"escape": "esc", "return": "enter"}
    normalized = aliases.get(normalized, normalized)
    if len(normalized) == 1 and normalized.isalnum():
        return normalized
    allowed = {
        *_HYPRLAND_KEYS,
        "space", "enter", "tab", "backspace", "delete", "esc",
        "ctrl", "ctrl_l", "ctrl_r", "alt", "alt_l", "alt_r",
        "shift", "shift_l", "shift_r", "caps_lock",
        "home", "end", "page_up", "page_down", "up", "down", "left", "right",
    }
    if normalized not in allowed:
        raise HotkeyError(f"Unsupported push-to-talk key: {key!r}.")
    return normalized


def _hyprland_key(key: str) -> str:
    names = {
        "space": "SPACE", "enter": "RETURN", "esc": "ESCAPE",
        "page_up": "PAGE_UP", "page_down": "PAGE_DOWN",
    }
    return names.get(normalize_key(key), normalize_key(key).upper())


def _parse_hyprland_binds(output: str) -> list[dict[str, str]]:
    records = []
    for block in output.split("\n\n"):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines or not lines[0].startswith("bind"):
            continue
        record = {"type": lines[0]}
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                record[key.strip()] = value.strip()
        records.append(record)
    return records


def _run_hyprctl(args: list[str]) -> str:
    executable = shutil.which("hyprctl")
    if not executable:
        raise HotkeyError("hyprctl is required for Hyprland global hotkeys.")
    result = subprocess.run(
        [executable, *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )
    unexpected_keyword_output = (
        args[0] == "keyword" and result.stdout.strip() not in ("", "ok")
    )
    if result.returncode != 0 or unexpected_keyword_output:
        detail = result.stderr.strip() or result.stdout.strip() or "no error details"
        raise HotkeyError(f"hyprctl {' '.join(args[:2])} failed: {detail}")
    return result.stdout


def _bindings_for_key(key: str) -> list[dict[str, str]]:
    hypr_key = _hyprland_key(key)
    return [
        record for record in _parse_hyprland_binds(_run_hyprctl(["binds"]))
        if record.get("key", "").upper() == hypr_key and record.get("modmask") == "0"
    ]


def hotkey_options() -> list[dict[str, object]]:
    if detect_backend() != "hyprland":
        return []
    records = _parse_hyprland_binds(_run_hyprctl(["binds"]))
    options = []
    for key in _HYPRLAND_KEYS:
        hypr_key = _hyprland_key(key)
        conflicts = [
            record for record in records
            if record.get("key", "").upper() == hypr_key
            and record.get("modmask") == "0"
            if not record.get("description", "").startswith(_MURMUR_DESCRIPTION)
        ]
        descriptions = [record.get("description") or record.get("arg", "unknown binding") for record in conflicts]
        options.append({"key": key, "available": not conflicts, "conflicts": descriptions})
    return options


class WindowsHotkeyBackend:
    name = "windows"

    def __init__(self, key: str, on_press: Callable, on_release: Callable):
        # Preserve the keyboard package's existing free-form Windows key names.
        self.key = key
        self.on_press = on_press
        self.on_release = on_release

    def start(self):
        import keyboard

        held = False

        def on_key_event(event):
            nonlocal held
            if event.event_type == keyboard.KEY_DOWN and not held:
                held = True
                threading.Thread(target=self.on_press, daemon=True).start()
            elif event.event_type == keyboard.KEY_UP and held:
                held = False
                threading.Thread(target=self.on_release, daemon=True).start()

        def listen():
            keyboard.hook_key(self.key, on_key_event, suppress=True)
            keyboard.wait()

        threading.Thread(target=listen, daemon=True).start()

    def stop(self):
        import keyboard
        keyboard.unhook_all()


def _pynput_key(key_str: str):
    from pynput import keyboard
    normalized = key_str.lower()
    special = {
        **{f"f{i}": getattr(keyboard.Key, f"f{i}") for i in range(1, 13)},
        "space": keyboard.Key.space, "enter": keyboard.Key.enter, "tab": keyboard.Key.tab,
        "backspace": keyboard.Key.backspace, "delete": keyboard.Key.delete,
        "esc": keyboard.Key.esc, "escape": keyboard.Key.esc,
        "ctrl": keyboard.Key.ctrl, "ctrl_l": keyboard.Key.ctrl_l, "ctrl_r": keyboard.Key.ctrl_r,
        "alt": keyboard.Key.alt, "alt_l": keyboard.Key.alt_l, "alt_r": keyboard.Key.alt_r,
        "shift": keyboard.Key.shift, "shift_l": keyboard.Key.shift_l, "shift_r": keyboard.Key.shift_r,
        "caps_lock": keyboard.Key.caps_lock,
        "up": keyboard.Key.up, "down": keyboard.Key.down,
        "left": keyboard.Key.left, "right": keyboard.Key.right,
        "home": keyboard.Key.home, "end": keyboard.Key.end,
        "page_up": keyboard.Key.page_up, "page_down": keyboard.Key.page_down,
    }
    # Preserve the previous X11 behavior for arbitrary character keys. Key
    # validation is intentionally stricter only in the Hyprland backend.
    return special.get(normalized, normalized)


class X11HotkeyBackend:
    name = "x11"

    def __init__(self, key: str, on_press: Callable, on_release: Callable):
        self.key = key
        self.on_press = on_press
        self.on_release = on_release
        self.listener = None

    def start(self):
        from pynput import keyboard
        target = _pynput_key(self.key)
        held = False

        def matches(key):
            if isinstance(target, keyboard.Key):
                return key == target
            return getattr(key, "char", None) == target

        def on_press(key):
            nonlocal held
            if matches(key) and not held:
                held = True
                threading.Thread(target=self.on_press, daemon=True).start()

        def on_release(key):
            nonlocal held
            if matches(key) and held:
                held = False
                threading.Thread(target=self.on_release, daemon=True).start()

        self.listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.listener.start()

    def stop(self):
        if self.listener is not None:
            self.listener.stop()
            self.listener = None


class HyprlandHotkeyBackend:
    name = "hyprland"

    def __init__(self, key: str, on_press: Callable, on_release: Callable):
        self.key = normalize_key(key)
        self.hypr_key = _hyprland_key(key)
        self.on_press = on_press
        self.on_release = on_release
        self.token = uuid.uuid4().hex[:8]
        runtime_dir = app_paths.runtime_directory()
        self.socket_path = runtime_dir / f"hotkey-{os.getpid()}-{self.token}.sock"
        self._socket = None
        self._thread = None
        self._stop_event = threading.Event()
        self._registered = False

    def _remove_stale_binding(self, records: list[dict[str, str]]):
        stale = [r for r in records if r.get("description", "").startswith(_MURMUR_DESCRIPTION)]
        if stale:
            _run_hyprctl(["keyword", "unbind", f", {self.hypr_key}"])

    def _check_conflicts(self):
        records = _bindings_for_key(self.key)
        conflicts = [r for r in records if not r.get("description", "").startswith(_MURMUR_DESCRIPTION)]
        if conflicts:
            details = "; ".join(r.get("description") or r.get("arg", "unknown binding") for r in conflicts)
            raise HotkeyError(f"{self.hypr_key} is already bound in Hyprland: {details}")
        self._remove_stale_binding(records)

    def _serve(self):
        while not self._stop_event.is_set():
            try:
                event = self._socket.recv(16).decode("ascii")
            except (OSError, UnicodeError):
                break
            callback = self.on_press if event == "press" else self.on_release if event == "release" else None
            if callback:
                threading.Thread(target=callback, daemon=True).start()

    def _command(self, event: str) -> str:
        return shlex.join([
            sys.executable,
            str(Path(__file__).resolve()),
            "emit",
            str(self.socket_path),
            event,
            self.hypr_key,
        ])

    def start(self):
        self._check_conflicts()
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self._socket.bind(str(self.socket_path))
        os.chmod(self.socket_path, 0o600)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

        try:
            _run_hyprctl([
                "keyword", "bindd",
                f", {self.hypr_key}, {_MURMUR_DESCRIPTION} press [{self.token}], exec, {self._command('press')}",
            ])
            self._registered = True
            _run_hyprctl([
                "keyword", "binddr",
                f", {self.hypr_key}, {_MURMUR_DESCRIPTION} release [{self.token}], exec, {self._command('release')}",
            ])
        except Exception:
            self.stop()
            raise

    def stop(self):
        if self._registered:
            try:
                _run_hyprctl(["keyword", "unbind", f", {self.hypr_key}"])
            except HotkeyError:
                pass
        self._registered = False
        self._stop_event.set()
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        try:
            self.socket_path.unlink()
        except FileNotFoundError:
            pass


class UnsupportedWaylandBackend:
    name = "unsupported-wayland"

    def start(self):
        raise HotkeyError(
            "This Wayland compositor has no supported Murmur hotkey backend."
        )

    def stop(self):
        pass


def create_backend(key: str, on_press: Callable, on_release: Callable):
    backend = detect_backend()
    if backend == "windows":
        return WindowsHotkeyBackend(key, on_press, on_release)
    if backend == "x11":
        return X11HotkeyBackend(key, on_press, on_release)
    if backend == "hyprland":
        return HyprlandHotkeyBackend(key, on_press, on_release)
    return UnsupportedWaylandBackend()


def capture_mode() -> str:
    return "select" if detect_backend() in ("hyprland", "unsupported-wayland") else "capture"


def _emit(socket_path: str, event: str, hypr_key: str) -> int:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        client.sendto(event.encode("ascii"), socket_path)
        return 0
    except OSError:
        # A crashed Murmur can leave a runtime binding until the key is next
        # pressed. Only remove it when its command still names this socket.
        try:
            records = _parse_hyprland_binds(_run_hyprctl(["binds"]))
            if any(socket_path in record.get("arg", "") for record in records):
                _run_hyprctl(["keyword", "unbind", f", {hypr_key}"])
        except HotkeyError:
            pass
        return 1
    finally:
        client.close()


if __name__ == "__main__" and len(sys.argv) == 5 and sys.argv[1] == "emit":
    raise SystemExit(_emit(sys.argv[2], sys.argv[3], sys.argv[4]))
