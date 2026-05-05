from pathlib import Path

import webview

_UI = Path(__file__).parent / "ui" / "splash.html"


class SplashAPI:
    def get_status(self):
        return "Loading speech model..."


class SplashScreen:
    def __init__(self):
        self._window: webview.Window | None = None

    def create(self) -> webview.Window:
        api = SplashAPI()
        self._window = webview.create_window(
            "Murmur",
            url=str(_UI),
            js_api=api,
            width=320,
            height=160,
            resizable=False,
            frameless=True,
            on_top=True,
            background_color="#1c1c1e",
        )
        return self._window

    def hide(self):
        if self._window:
            self._window.destroy()
            self._window = None
