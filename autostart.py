import os
import sys
from pathlib import Path

_APP_NAME = "Murmur"


def _command() -> str:
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    return f'"{sys.executable}" "{script}"'


# ── Windows (registry) ────────────────────────────────────────────────────────

if sys.platform == "win32":
    import winreg

    _KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

    def is_enabled() -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY_PATH, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, _APP_NAME)
            return True
        except OSError:
            return False

    def set_enabled(enabled: bool):
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _command())
            else:
                try:
                    winreg.DeleteValue(key, _APP_NAME)
                except OSError:
                    pass


# ── Linux (XDG autostart .desktop file) ──────────────────────────────────────

else:
    _DESKTOP_DIR = Path.home() / ".config" / "autostart"
    _DESKTOP_FILE = _DESKTOP_DIR / "murmur.desktop"

    def is_enabled() -> bool:
        return _DESKTOP_FILE.exists()

    def set_enabled(enabled: bool):
        if enabled:
            _DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
            _DESKTOP_FILE.write_text(
                "[Desktop Entry]\n"
                f"Name={_APP_NAME}\n"
                "Type=Application\n"
                f"Exec={_command()}\n"
                "Hidden=false\n"
                "NoDisplay=false\n"
                "X-GNOME-Autostart-enabled=true\n",
                encoding="utf-8",
            )
        else:
            try:
                _DESKTOP_FILE.unlink()
            except FileNotFoundError:
                pass
