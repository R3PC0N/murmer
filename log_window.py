from pathlib import Path

import sys

import webview

import logger
from theme_utils import apply_title_bar_theme

_UI = Path(__file__).parent / "ui" / "log.html"


class LogAPI:
    def get_log(self) -> list:
        return list(logger.get_buffer())

    def clear_log(self):
        logger.clear_buffer()

    def open_history(self):
        logger.open_history()


class LogWindow:
    def __init__(self):
        self._window: webview.Window | None = None

    def open(self):
        if self._window:
            try:
                self._window.show()
                return
            except Exception:
                self._window = None

        api = LogAPI()
        self._window = webview.create_window(
            "Murmur Activity",
            url=str(_UI),
            js_api=api,
            width=580,
            height=420,
            background_color="#232326",
        )
        self._window.events.loaded += lambda: apply_title_bar_theme(self._window)
        self._window.events.closed += self._on_closed

        if sys.platform != "win32":
            from gi.repository import GLib
            for _ in range(20):
                GLib.MainContext.default().iteration(False)
            try:
                self._window.show()
            except Exception:
                pass

    def _on_closed(self):
        self._window = None
