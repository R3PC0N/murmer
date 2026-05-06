import sys
import threading
from pathlib import Path

import webview

import autostart
import config
from recorder import device_available, get_device_names
from theme_utils import apply_title_bar_theme

_UI = Path(__file__).parent / "ui" / "settings.html"


class SettingsAPI:
    def __init__(self, on_save=None, on_restart=None):
        self._on_save = on_save
        self._on_restart = on_restart
        self._capturing = False

    def get_config(self) -> dict:
        current = config.AUDIO_DEVICE
        ok = device_available(current)
        return {
            "PUSH_TO_TALK_KEY":       config.PUSH_TO_TALK_KEY,
            "AUTO_START":             autostart.is_enabled(),
            "AUDIO_DEVICE":           current,
            "WHISPER_MODEL":          config.WHISPER_MODEL,
            "WHISPER_DEVICE":         config.WHISPER_DEVICE,
            "TRANSCRIPTION_MODE":     config.TRANSCRIPTION_MODE,
            "REMOTE_WHISPER_URL":     config.REMOTE_WHISPER_URL,
            "REMOTE_WHISPER_API_KEY": config.REMOTE_WHISPER_API_KEY,
            "SAVED_SERVERS":          list(config.SAVED_SERVERS),
            "AI_CLEANUP_ENABLED":     config.AI_CLEANUP_ENABLED,
            "ANTHROPIC_API_KEY":      config.ANTHROPIC_API_KEY,
            "BEEP_ENABLED":           config.BEEP_ENABLED,
            "SHOW_OVERLAY":           config.SHOW_OVERLAY,
            "TRANSCRIPTION_STYLE":    config.TRANSCRIPTION_STYLE,
            "CUSTOM_STYLE_PROMPT":    config.CUSTOM_STYLE_PROMPT,
            "USER_PROFILE":           config.USER_PROFILE,
            "WORD_CORRECTIONS":       dict(config.WORD_CORRECTIONS),
            "_device_ok":             ok,
        }

    def get_devices(self) -> list:
        return get_device_names()

    def capture_hotkey(self) -> str:
        if self._capturing:
            return ""
        self._capturing = True
        try:
            if sys.platform == "win32":
                import keyboard
                key = keyboard.read_key(suppress=True)
            else:
                from pynput import keyboard as _pk
                captured = [None]

                def on_press(k):
                    try:
                        captured[0] = k.name if hasattr(k, "name") else k.char
                    except AttributeError:
                        captured[0] = str(k)
                    return False

                with _pk.Listener(on_press=on_press) as lst:
                    lst.join()
                key = captured[0] or "f9"
            return key
        finally:
            self._capturing = False

    def save_server(self, name: str, url: str, api_key: str) -> list:
        servers = [s for s in config.SAVED_SERVERS if s["name"] != name]
        servers.append({"name": name, "url": url, "api_key": api_key})
        config.save({"SAVED_SERVERS": servers})
        return list(config.SAVED_SERVERS)

    def delete_server(self, name: str) -> list:
        servers = [s for s in config.SAVED_SERVERS if s["name"] != name]
        config.save({"SAVED_SERVERS": servers})
        return list(config.SAVED_SERVERS)

    def save_settings(self, updates: dict, restart: bool = False):
        auto = updates.pop("AUTO_START", None)
        config.save(updates)
        if auto is not None:
            autostart.set_enabled(bool(auto))
        if self._on_save:
            self._on_save(updates)
        if restart and self._on_restart:
            threading.Thread(target=self._on_restart, daemon=True).start()


class SettingsWindow:
    def __init__(self, on_save=None, on_restart=None):
        self._on_save = on_save
        self._on_restart = on_restart
        self._window: webview.Window | None = None

    def open(self):
        import threading
        print(f"[DBG] SettingsWindow.open() thread={threading.current_thread().name} _window={self._window}", flush=True)
        if self._window:
            try:
                self._window.show()
                print("[DBG] show() called on existing window", flush=True)
                return
            except Exception as e:
                print(f"[DBG] show() failed: {e}", flush=True)
                self._window = None

        api = SettingsAPI(on_save=self._on_save, on_restart=self._on_restart)
        self._window = webview.create_window(
            "Murmur Settings",
            url=str(_UI),
            js_api=api,
            width=740,
            height=540,
            min_size=(600, 420),
            background_color="#232326",
        )
        print(f"[DBG] create_window returned: {self._window}", flush=True)
        self._window.events.loaded += lambda: apply_title_bar_theme(self._window)
        self._window.events.closed += self._on_closed

    def _on_closed(self):
        self._window = None
