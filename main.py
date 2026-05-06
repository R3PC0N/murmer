# ── Heavy imports ─────────────────────────────────────────────────────────────
import ctypes
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

import pystray
import webview
from PIL import Image, ImageDraw

import config
import logger
from log_window import LogWindow
from overlay import RecordingOverlay
from server_manager_window import ServerManagerWindow
from paster import paste_text
from recorder import Recorder
from settings_window import SettingsWindow
from splash import SplashScreen
from theme_utils import start_theme_watcher
from transcriber import Transcriber

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ── Window icon (transparent background, amber bars) ─────────────────────────

def _build_transparent_ico() -> str:
    import tempfile
    heights_ratio = [0.25, 0.45, 0.65, 0.85, 0.65, 0.45, 0.25]
    sizes = [16, 32, 48, 256]
    images = []
    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        bar_w = max(2, int(size * 0.08))
        gap   = max(1, int(size * 0.045))
        n     = len(heights_ratio)
        total_w = n * bar_w + (n - 1) * gap
        sx    = (size - total_w) // 2
        cy    = size // 2
        inner_h = size * 0.72
        bar_r = max(1, bar_w // 2)
        for i, ratio in enumerate(heights_ratio):
            h = max(2, int(inner_h * ratio))
            x = sx + i * (bar_w + gap)
            d.rounded_rectangle(
                [x, cy - h // 2, x + bar_w - 1, cy + h // 2],
                radius=bar_r, fill="#C8922A",
            )
        images.append(img)
    # gdk-pixbuf on Linux does not support compressed .ico files; use .png instead.
    if sys.platform == "win32":
        tmp = tempfile.NamedTemporaryFile(suffix=".ico", delete=False)
        tmp.close()
        images[0].save(tmp.name, format="ICO", append_images=images[1:],
                       sizes=[(s, s) for s in sizes])
    else:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        images[-1].save(tmp.name, format="PNG")  # use the largest size (256px)
    return tmp.name


# ── Audio feedback ────────────────────────────────────────────────────────────

def _beep(frequency: int, duration_ms: int):
    if not config.BEEP_ENABLED:
        return
    if sys.platform == "win32":
        import winsound
        winsound.Beep(frequency, duration_ms)
    else:
        import numpy as np
        import sounddevice as sd
        n = int(44100 * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, n, endpoint=False)
        tone = (np.sin(2 * np.pi * frequency * t) * 0.3).astype(np.float32)
        sd.play(tone, 44100)


# ── Single instance ───────────────────────────────────────────────────────────
_mutex = None
_lock_file = None
_pynput_listener = None

def _ensure_single_instance():
    global _mutex, _lock_file
    if sys.platform == "win32":
        _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\MurmurSingleInstance")
        if ctypes.windll.kernel32.GetLastError() == 183:
            sys.exit(0)
    else:
        import fcntl, tempfile
        lock_path = Path(tempfile.gettempdir()) / "murmur.lock"
        _lock_file = open(lock_path, "w")
        try:
            fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            sys.exit(0)


# ── State ─────────────────────────────────────────────────────────────────────
_recording   = False
_processing  = False
_icon: pystray.Icon | None = None
_server_proc: subprocess.Popen | None = None
_overlay: RecordingOverlay | None = None

recorder    = Recorder()
transcriber = Transcriber()
cleaner     = None

settings_win: SettingsWindow | None = None
log_win: LogWindow | None = None
server_manager_win: ServerManagerWindow | None = None
splash: SplashScreen | None = None


# ── Cleaner ───────────────────────────────────────────────────────────────────

def _load_cleaner():
    global cleaner
    cleaner = None
    if config.AI_CLEANUP_ENABLED and config.ANTHROPIC_API_KEY:
        from cleaner import Cleaner
        cleaner = Cleaner()
        logger.log("AI cleanup enabled (Claude Haiku).", level="INFO")
    else:
        logger.log("AI cleanup disabled.", level="INFO")


# ── Tray icon ─────────────────────────────────────────────────────────────────

def _make_icon(recording=False, processing=False) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if recording:
        color = "#D94040"
    elif processing:
        color = "#C8922A"
    else:
        color = "#AEAEB2"
    heights = [14, 24, 38, 52, 38, 24, 14]
    bar_w, gap = 6, 3
    total_w = len(heights) * bar_w + (len(heights) - 1) * gap
    sx = (64 - total_w) // 2
    cy = 32
    for i, h in enumerate(heights):
        x = sx + i * (bar_w + gap)
        d.rounded_rectangle([x, cy - h // 2, x + bar_w - 1, cy + h // 2],
                             radius=2, fill=color)
    return img


def _gtk_dispatch(fn):
    """Schedule fn on the GTK main thread. Required for all pystray/GTK calls
    that originate from recording/hotkey threads on Linux."""
    if sys.platform != "win32":
        from gi.repository import GLib
        GLib.idle_add(lambda: fn() or False)
    else:
        fn()


def _update_icon():
    if not _icon:
        return
    new_icon = _make_icon(recording=_recording, processing=_processing)
    if sys.platform != "win32":
        _gtk_dispatch(lambda: setattr(_icon, "icon", new_icon))
    else:
        _icon.icon = new_icon


# ── Recording ─────────────────────────────────────────────────────────────────

def _on_press():
    global _recording
    if _recording or _processing:
        return
    _recording = True
    _update_icon()
    _beep(880, 80)
    recorder.start()
    print("[DBG] recording started")
    if config.SHOW_OVERLAY and _overlay:
        _overlay.show()


def _on_release():
    global _recording, _processing
    if not _recording:
        return
    audio = recorder.stop()
    _recording = False
    if _overlay:
        _overlay.hide()

    samples = len(audio) if audio is not None else 0
    print(f"[DBG] recording stopped — {samples} samples")
    if audio is None or samples == 0:
        logger.log("No audio captured — check your microphone input in Settings → Audio.", level="ERROR")
        _beep(220, 400)
        _update_icon()
        return
    if samples < config.MIN_RECORDING_SAMPLES:
        logger.log("Recording too short — hold the key a little longer.", level="ERROR")
        _beep(440, 120)
        _update_icon()
        return

    _processing = True
    _update_icon()
    threading.Thread(target=_process, args=(audio,), daemon=True).start()


def _apply_corrections(text: str) -> str:
    corrections = config.WORD_CORRECTIONS
    if not corrections:
        return text
    for wrong, right in corrections.items():
        text = re.sub(r'\b' + re.escape(wrong) + r'\b', right, text, flags=re.IGNORECASE)
    return text


def _process(audio):
    global _processing
    try:
        print("[DBG] transcribing...")
        text, language = transcriber.transcribe(audio)
        print(f"[DBG] transcribe result: {repr(text)}")
        if not text:
            logger.log("Transcription returned empty result.", level="ERROR")
            return
        logger.log(f"Transcribed ({language}): {text}")
        text = _apply_corrections(text)
        if cleaner and config.AI_CLEANUP_ENABLED:
            text = cleaner.clean(text, language)
            logger.log(f"Cleaned: {text}", level="RESULT")
        else:
            logger.log(f"Result: {text}", level="RESULT")
        paste_text(text)
        _beep(660, 80)
    except Exception as e:
        logger.log(f"Error: {e}", level="ERROR")
        _beep(300, 250)
    finally:
        _processing = False
        _update_icon()


# ── Hotkey listener ───────────────────────────────────────────────────────────

def _pynput_key(key_str: str):
    from pynput import keyboard as _pk
    special = {
        **{f'f{i}': getattr(_pk.Key, f'f{i}') for i in range(1, 13)},
        'space': _pk.Key.space, 'enter': _pk.Key.enter, 'tab': _pk.Key.tab,
        'backspace': _pk.Key.backspace, 'delete': _pk.Key.delete,
        'esc': _pk.Key.esc, 'escape': _pk.Key.esc,
        'ctrl': _pk.Key.ctrl, 'ctrl_l': _pk.Key.ctrl_l, 'ctrl_r': _pk.Key.ctrl_r,
        'alt': _pk.Key.alt, 'alt_l': _pk.Key.alt_l, 'alt_r': _pk.Key.alt_r,
        'shift': _pk.Key.shift, 'shift_l': _pk.Key.shift_l, 'shift_r': _pk.Key.shift_r,
        'caps_lock': _pk.Key.caps_lock,
        'up': _pk.Key.up, 'down': _pk.Key.down, 'left': _pk.Key.left, 'right': _pk.Key.right,
        'home': _pk.Key.home, 'end': _pk.Key.end,
        'page_up': _pk.Key.page_up, 'page_down': _pk.Key.page_down,
    }
    return special.get(key_str.lower(), key_str.lower())


def _pynput_key_matches(key, target) -> bool:
    from pynput import keyboard as _pk
    if isinstance(target, _pk.Key):
        return key == target
    try:
        return key.char == target
    except AttributeError:
        return False


def _keyboard_listener():
    global _pynput_listener
    _held = False

    if sys.platform == "win32":
        import keyboard
        def on_key_event(event):
            nonlocal _held
            if event.event_type == keyboard.KEY_DOWN and not _held:
                _held = True
                threading.Thread(target=_on_press, daemon=True).start()
            elif event.event_type == keyboard.KEY_UP and _held:
                _held = False
                threading.Thread(target=_on_release, daemon=True).start()
        keyboard.hook_key(config.PUSH_TO_TALK_KEY, on_key_event, suppress=True)
        keyboard.wait()
    else:
        from pynput import keyboard as _pk
        target = _pynput_key(config.PUSH_TO_TALK_KEY)

        def on_press(key):
            nonlocal _held
            if _pynput_key_matches(key, target) and not _held:
                _held = True
                threading.Thread(target=_on_press, daemon=True).start()

        def on_release(key):
            nonlocal _held
            if _pynput_key_matches(key, target) and _held:
                _held = False
                threading.Thread(target=_on_release, daemon=True).start()

        with _pk.Listener(on_press=on_press, on_release=on_release) as listener:
            _pynput_listener = listener
            listener.join()
        _pynput_listener = None


def _stop_hotkey_listener():
    global _pynput_listener
    if sys.platform == "win32":
        import keyboard
        keyboard.unhook_all()
    else:
        if _pynput_listener is not None:
            _pynput_listener.stop()


# ── Whisper server ────────────────────────────────────────────────────────────

def _server_port_in_use() -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", 8765)) == 0


def _server_running() -> bool:
    if _server_proc is not None and _server_proc.poll() is None:
        return True
    return _server_port_in_use()


def _start_whisper_server():
    global _server_proc
    if _server_running():
        return
    script = Path(__file__).parent / "server" / "faster_whisper_server.py"
    venv_bin = "Scripts" if sys.platform == "win32" else "bin"
    python_name = "python.exe" if sys.platform == "win32" else "python"
    python = Path(__file__).parent / "server" / "venv" / venv_bin / python_name
    if not python.exists() or not script.exists():
        logger.log("Whisper Server: files not found. Run the server setup first.", level="ERROR")
        return
    _server_proc = subprocess.Popen(
        [str(python), str(script)],
        cwd=str(script.parent),
        creationflags=_NO_WINDOW,
    )
    logger.log("Whisper Server gestart op poort 8765.", level="OK")
    if _icon:
        _gtk_dispatch(_icon.update_menu)


def _stop_whisper_server():
    global _server_proc
    if _server_proc and _server_proc.poll() is None:
        _server_proc.terminate()
        try:
            _server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_proc.kill()
    _server_proc = None
    if sys.platform == "win32":
        subprocess.run(
            ["powershell", "-Command",
             "Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like "
             "'*faster_whisper_server*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
            creationflags=_NO_WINDOW, capture_output=True,
        )
    else:
        subprocess.run(["pkill", "-f", "faster_whisper_server"], capture_output=True)
    logger.log("Whisper Server gestopt.", level="OK")
    if _icon:
        _gtk_dispatch(_icon.update_menu)


# ── Window openers ────────────────────────────────────────────────────────────

def _open_settings():
    print("[DBG] _open_settings called", flush=True)
    if settings_win:
        _gtk_dispatch(settings_win.open)


def _open_log():
    print("[DBG] _open_log called", flush=True)
    if log_win:
        _gtk_dispatch(log_win.open)


def _open_server_manager():
    print("[DBG] _open_server_manager called", flush=True)
    if server_manager_win:
        _gtk_dispatch(server_manager_win.open)


def _on_settings_saved(updates: dict):
    _load_cleaner()
    if "PUSH_TO_TALK_KEY" in updates:
        _stop_hotkey_listener()
        threading.Thread(target=_keyboard_listener, daemon=True).start()
        logger.log(f"Hotkey updated to: {config.PUSH_TO_TALK_KEY}", level="INFO")
    logger.log("Settings saved.", level="INFO")


# ── Restart / Quit ────────────────────────────────────────────────────────────

def _release_lock():
    global _mutex, _lock_file
    if sys.platform == "win32":
        if _mutex:
            ctypes.windll.kernel32.CloseHandle(_mutex)
            _mutex = None
    else:
        if _lock_file:
            import fcntl
            fcntl.flock(_lock_file, fcntl.LOCK_UN)
            _lock_file.close()
            _lock_file = None


def _restart():
    _release_lock()
    _stop_hotkey_listener()
    if _icon:
        _icon.stop()
    for win in list(webview.windows):
        try:
            win.destroy()
        except Exception:
            pass
    os.execv(sys.executable, [sys.executable] + sys.argv)


def _quit():
    _stop_hotkey_listener()
    if _server_running():
        _stop_whisper_server()
    if _icon:
        _icon.stop()
    for win in list(webview.windows):
        try:
            win.destroy()
        except Exception:
            pass


# ── Overlay (plain tkinter in its own thread) ─────────────────────────────────

def _start_overlay_thread():
    global _overlay
    import tkinter as tk

    ready = threading.Event()

    def _run():
        global _overlay
        tk_root = tk.Tk()
        tk_root.withdraw()
        _overlay = RecordingOverlay(tk_root)
        ready.set()
        tk_root.mainloop()

    threading.Thread(target=_run, daemon=True).start()
    ready.wait(timeout=3)


# ── Background init ───────────────────────────────────────────────────────────

def _background_init():
    global _icon

    from recorder import device_available
    if not device_available(config.AUDIO_DEVICE):
        dev = config.AUDIO_DEVICE or "Default"
        logger.log(f"⚠ Audio device not detected: {dev}. Check Settings → Audio.", level="ERROR")
    else:
        dev = config.AUDIO_DEVICE or "Default"
        logger.log(f"Audio device: {dev}")

    if config.WHISPER_SERVER_AUTOSTART:
        _start_whisper_server()

    transcriber.load()
    _load_cleaner()

    key = config.PUSH_TO_TALK_KEY.upper()
    logger.log(f"Ready. Hold {key} to record, release to transcribe and paste.", level="INFO")

    menu = pystray.Menu(
        pystray.MenuItem("Murmur", None, enabled=False),
        pystray.MenuItem(f"Hold {key} to record", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Settings",         lambda icon, item: _open_settings()),
        pystray.MenuItem("Activity log",     lambda icon, item: _open_log()),
        pystray.MenuItem("Open history",     lambda icon, item: logger.open_history()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Whisper Server...", lambda icon, item: _open_server_manager()),
        pystray.MenuItem(
            lambda item: "● Server running" if _server_running() else "○ Server stopped",
            None, enabled=False,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Restart", lambda icon, item: threading.Thread(target=_restart, daemon=True).start()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", lambda icon, item: _quit()),
    )
    _icon = pystray.Icon("murmur", _make_icon(), "Murmur", menu)

    threading.Thread(target=_keyboard_listener, daemon=True).start()

    if sys.platform == "win32":
        _icon.run_detached()
    else:
        # On Linux, webview already runs Gtk.main() on the main thread.
        # Calling _icon.run() in a thread starts a competing Gtk.main() on the
        # same GLib context, causing threading conflicts.
        # Fix: run _icon.run() on the GTK main thread via idle_add with Gtk.main
        # and Gtk.main_quit both stubbed so pystray does its AppIndicator setup
        # without touching the event loop. After run() returns, pystray's cleanup
        # sets _running=False and shuts down its executor; we restore both so
        # menu callbacks keep working.
        import concurrent.futures
        from gi.repository import GLib

        def _init_pystray_on_gtk_thread():
            print("[DBG] _init_pystray_on_gtk_thread fired", flush=True)
            try:
                from gi.repository import Gtk
                _orig_main = Gtk.main
                _orig_quit = Gtk.main_quit
                Gtk.main = lambda: None
                Gtk.main_quit = lambda: None
                try:
                    _icon.run()
                finally:
                    Gtk.main = _orig_main
                    Gtk.main_quit = _orig_quit
                print(f"[DBG] after run(): _running={_icon._running}, "
                      f"attrs={[a for a in dir(_icon) if not a.startswith('__')]}", flush=True)
                # Restore state pystray's cleanup tore down.
                _icon._running = True
                _icon._executor = concurrent.futures.ThreadPoolExecutor()
                if hasattr(_icon, "_indicator"):
                    from gi.repository import AppIndicator3
                    _icon._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
                    print("[DBG] indicator re-activated", flush=True)
                else:
                    print(f"[DBG] no _indicator attr; icon type={type(_icon)}", flush=True)
                # Verify idle_add dispatch works by scheduling a test print.
                GLib.idle_add(lambda: print("[DBG] GLib.idle_add test fired", flush=True) or False)
            except Exception as e:
                print(f"[DBG] pystray init exception: {e}", flush=True)
                logger.log(f"Tray icon init error: {e}", level="ERROR")
            return False  # idle_add: run once

        GLib.idle_add(_init_pystray_on_gtk_thread)

    if splash:
        splash.hide()

    def _get_open_windows():
        wins = []
        for w in [settings_win, log_win, server_manager_win]:
            if w and w._window:
                wins.append(w._window)
        return wins
    start_theme_watcher(_get_open_windows)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    global settings_win, log_win, server_manager_win, splash

    if sys.platform != "win32":
        import ctypes as _ct
        try:
            _ct.cdll.LoadLibrary("libX11.so.6").XInitThreads()
        except Exception:
            pass

    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MurmurLabs.Murmur.1")

    _ensure_single_instance()

    settings_win = SettingsWindow(on_save=_on_settings_saved, on_restart=_restart)
    log_win = LogWindow()
    server_manager_win = ServerManagerWindow(
        get_server_running=_server_running,
        start_server=_start_whisper_server,
        stop_server=_stop_whisper_server,
    )

    splash = SplashScreen()
    splash.create()

    _start_overlay_thread()

    _icon_path = _build_transparent_ico()
    webview.start(
        func=lambda: threading.Thread(target=_background_init, daemon=True).start(),
        icon=_icon_path,
        debug=False,
    )


if __name__ == "__main__":
    main()
