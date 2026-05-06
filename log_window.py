from pathlib import Path

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

    def create(self):
        """Pre-create the window hidden before webview.start(). Call once at startup."""
        api = LogAPI()
        self._window = webview.create_window(
            "Murmur Activity",
            url=str(_UI),
            js_api=api,
            width=580,
            height=420,
            background_color="#232326",
            hidden=True,
        )
        self._window.events.loaded += lambda: apply_title_bar_theme(self._window)
        self._window.events.closing += self._on_closing

    def _on_closing(self):
        self._window.hide()
        return False  # Cancel the close; keep window alive for reuse

    def open(self):
        if self._window:
            self._window.hidden = False
            self._window.show()
            if sys.platform != "win32":
                from gi.repository import GLib
                uid = self._window.uid
                def _force_show():
                    try:
                        from webview.platforms.gtk import BrowserView
                        view = BrowserView.instances.get(uid)
                        if view:
                            view.window.show_all()
                            view.window.present()
                    except Exception:
                        pass
                    return False
                GLib.idle_add(_force_show)
