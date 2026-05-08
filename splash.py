import ctypes
import sys
from pathlib import Path

import webview

from theme_utils import apply_title_bar_theme

_UI = Path(__file__).parent / "ui" / "splash.html"


class SplashAPI:
    def get_status(self):
        return "Starting up..."


class SplashScreen:
    def __init__(self):
        self._window: webview.Window | None = None

    def create(self) -> webview.Window:
        w, h = 320, 160
        if sys.platform == "win32":
            user32 = ctypes.windll.user32
            x = (user32.GetSystemMetrics(0) - w) // 2
            y = (user32.GetSystemMetrics(1) - h) // 2
        else:
            x = y = None
        api = SplashAPI()
        self._window = webview.create_window(
            "Murmur",
            url=str(_UI),
            js_api=api,
            width=w,
            height=h,
            x=x,
            y=y,
            resizable=False,
            frameless=True,
            on_top=True,
            background_color="#1c1c1e",
        )
        self._window.events.loaded += lambda: apply_title_bar_theme(self._window)
        return self._window

    def update_status(self, text: str):
        if self._window:
            safe = text.replace("\\", "\\\\").replace("'", "\\'")
            self._window.evaluate_js(
                f"var el = document.getElementById('status'); if (el) el.textContent = '{safe}';"
            )

    def hide(self):
        if self._window:
            self._window.hide()
            # Keep window alive to hold the webview event loop open
