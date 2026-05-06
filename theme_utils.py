import ctypes
import ctypes.wintypes
import sys
import threading


def _is_light_mode() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return bool(val)
    except Exception:
        return False


def _dwm_set(hwnd, is_dark: bool):
    # DWMWA_USE_IMMERSIVE_DARK_MODE
    val = ctypes.c_int(1 if is_dark else 0)
    for attr in (20, 19):
        if ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, attr, ctypes.byref(val), ctypes.sizeof(val)
        ) == 0:
            break

    # DWMWA_CAPTION_COLOR (attr 35, Windows 11+): set explicit caption colour.
    # This cannot be overridden by WebView2's internal compositor.
    # COLORREF format: 0x00BBGGRR
    # DWMWA_CAPTION_COLOR_NONE = 0xFFFFFFFE → revert to system default (dark mode)
    DWMWA_CAPTION_COLOR = 35
    if is_dark:
        color = ctypes.c_uint(0xFFFFFFFE)   # system default (dark)
    else:
        color = ctypes.c_uint(0x00F3F6F9)   # warm light, matches bg-surface
    ctypes.windll.dwmapi.DwmSetWindowAttribute(
        hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(color), ctypes.sizeof(color)
    )

    # Force non-client area redraw
    SWP_FLAGS = 0x0002 | 0x0001 | 0x0004 | 0x0020  # NOMOVE|NOSIZE|NOZORDER|FRAMECHANGED
    ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_FLAGS)


def _apply_for_title(title: str, is_dark: bool):
    import os
    pid = os.getpid()

    @ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    def _cb(hwnd, _):
        dpid = ctypes.wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(dpid))
        if dpid.value == pid:
            buf = ctypes.create_unicode_buffer(512)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, 512)
            if buf.value == title:
                _dwm_set(hwnd, is_dark)
        return True

    ctypes.windll.user32.EnumWindows(_cb, 0)


def apply_title_bar_theme(win):
    """Match the DWM title bar colour to the system light/dark preference.

    Delayed by 250 ms so WebView2 finishes its own compositor setup first.
    """
    if sys.platform != "win32":
        return
    try:
        title = win.title
    except Exception:
        return

    is_dark = not _is_light_mode()

    def _run():
        _apply_for_title(title, is_dark)

    threading.Timer(0.25, _run).start()


def start_theme_watcher(get_open_windows):
    """Poll system theme every 2 s and reapply title bar to all open windows.

    get_open_windows: callable returning a list of pywebview Window objects.
    """
    if sys.platform != "win32":
        return

    import os
    pid = os.getpid()
    _last = [_is_light_mode()]

    @ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    def _enum_cb(hwnd, _):
        dpid = ctypes.wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(dpid))
        if dpid.value == pid and ctypes.windll.user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(512)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, 512)
            if buf.value in _open_titles:
                _dwm_set(hwnd, _current_dark[0])
        return True

    _open_titles = set()
    _current_dark = [not _last[0]]

    def _watch():
        while True:
            threading.Event().wait(2)
            now_light = _is_light_mode()
            if now_light != _last[0]:
                _last[0] = now_light
                _current_dark[0] = not now_light
                try:
                    wins = get_open_windows()
                    _open_titles.clear()
                    for w in wins:
                        try:
                            _open_titles.add(w.title)
                        except Exception:
                            pass
                    ctypes.windll.user32.EnumWindows(_enum_cb, 0)
                except Exception:
                    pass

    threading.Thread(target=_watch, daemon=True).start()
