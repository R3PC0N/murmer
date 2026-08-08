"""Linux capability checks and desktop integration used by setup_linux.sh."""

import argparse
import ctypes.util
import importlib
import os
import shutil
import sys
from collections.abc import Callable, Mapping
from pathlib import Path


def detect_session(environ: Mapping[str, str] | None = None) -> tuple[str, bool]:
    environ = os.environ if environ is None else environ
    session_type = environ.get("XDG_SESSION_TYPE", "").lower()
    wayland = session_type == "wayland" or bool(environ.get("WAYLAND_DISPLAY"))
    x11 = session_type == "x11" or (not wayland and bool(environ.get("DISPLAY")))
    desktop = environ.get("XDG_CURRENT_DESKTOP", "").lower().split(":")
    session = "wayland" if wayland else "x11" if x11 else "unknown"
    return session, "hyprland" in desktop


def required_executables(environ: Mapping[str, str] | None = None) -> tuple[str, ...]:
    session, hyprland = detect_session(environ)
    required = ["xdg-open"]
    if session == "wayland":
        required.append("wtype")
        if hyprland:
            required.append("hyprctl")
    elif session == "x11":
        required.append("xdotool")
    return tuple(required)


def missing_executables(
    environ: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> list[str]:
    return [name for name in required_executables(environ) if which(name) is None]


def _check_python_capabilities() -> list[str]:
    missing = []
    for module, label in (("tkinter", "Tk"), ("gi", "PyGObject"), ("cairo", "Cairo")):
        try:
            importlib.import_module(module)
        except Exception:
            missing.append(label)

    if ctypes.util.find_library("portaudio") is None:
        missing.append("PortAudio")

    try:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk  # noqa: F401
    except Exception:
        missing.append("GTK3 typelib")

    webkit_available = False
    for version in ("4.1", "4.0"):
        try:
            import gi
            gi.require_version("WebKit2", version)
            from gi.repository import WebKit2  # noqa: F401
            webkit_available = True
            break
        except Exception:
            continue
    if not webkit_available:
        missing.append("WebKitGTK typelib")

    indicator_available = False
    for namespace in ("AyatanaAppIndicator3", "AppIndicator3"):
        try:
            import gi
            gi.require_version(namespace, "0.1")
            importlib.import_module(f"gi.repository.{namespace}")
            indicator_available = True
            break
        except Exception:
            continue
    if not indicator_available:
        missing.append("AppIndicator typelib")
    return missing


def desktop_quote(value: str) -> str:
    """Quote one Desktop Entry Exec argument according to the specification."""
    escaped = value.replace("\\", "\\\\")
    for character in ('"', "`", "$"):
        escaped = escaped.replace(character, f"\\{character}")
    return f'"{escaped}"'


def render_desktop_entry(python: Path, script: Path) -> str:
    return (
        "[Desktop Entry]\n"
        "Version=1.0\n"
        "Type=Application\n"
        "Name=Murmur\n"
        "Comment=Push-to-talk dictation and transcription\n"
        f"TryExec={python}\n"
        f"Exec={desktop_quote(str(python))} {desktop_quote(str(script))}\n"
        "Icon=murmur\n"
        "Terminal=false\n"
        "Categories=Utility;\n"
        "StartupNotify=false\n"
        "StartupWMClass=murmur\n"
    )


def install_desktop_entry(app_dir: Path, python: Path, environ=None) -> Path:
    environ = os.environ if environ is None else environ
    data_home = Path(environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    applications = data_home / "applications"
    icons = data_home / "icons/hicolor/scalable/apps"
    applications.mkdir(parents=True, exist_ok=True)
    icons.mkdir(parents=True, exist_ok=True)
    shutil.copy2(app_dir / "murmur.svg", icons / "murmur.svg")
    desktop_file = applications / "murmur.desktop"
    desktop_file.write_text(
        render_desktop_entry(python.absolute(), (app_dir / "main.py").resolve()),
        encoding="utf-8",
    )
    return desktop_file


def check() -> int:
    missing = _check_python_capabilities()
    missing.extend(missing_executables())
    session, hyprland = detect_session()
    print(f"Desktop session: {session}" + (" (Hyprland)" if hyprland else ""))
    if missing:
        print("Missing Linux prerequisites:", file=sys.stderr)
        for item in missing:
            print(f"  - {item}", file=sys.stderr)
        print(
            "Install the packages listed for your distribution in README.md, "
            "then rerun setup.",
            file=sys.stderr,
        )
        return 1
    print("Linux capability checks passed.")
    print("A StatusNotifier tray host must be running for the Murmur tray icon to be visible.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("check", "install-desktop"))
    parser.add_argument("--app-dir", type=Path, default=Path(__file__).parent)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    args = parser.parse_args()
    if args.command == "check":
        return check()
    desktop_file = install_desktop_entry(args.app_dir.resolve(), args.python)
    print(f"Desktop entry installed: {desktop_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
