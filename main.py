# ── X11 thread safety (must be before any tkinter or GTK import) ─────────────
import sys as _sys
if _sys.platform != "win32":
    import ctypes as _ctypes
    try:
        _ctypes.cdll.LoadLibrary("libX11.so.6").XInitThreads()
    except Exception:
        pass
    del _ctypes
del _sys

# ── Early window (shown immediately before heavy imports) ─────────────────────
import tkinter as _tk

def _show_early_window():
    win = _tk.Tk()
    win.overrideredirect(True)
    win.configure(bg="#1c1c1e")
    win.attributes("-topmost", True)
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    w, h = 300, 90
    win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
    _tk.Label(win, text="Murmer", fg="#ffffff", bg="#1c1c1e",
              font=("Segoe UI", 24, "bold")).place(relx=0.5, rely=0.38, anchor="center")
    _tk.Label(win, text="Starting...", fg="#666666", bg="#1c1c1e",
              font=("Segoe UI", 11)).place(relx=0.5, rely=0.72, anchor="center")
    win.update()
    return win

_early_win = _show_early_window()

# ── Heavy imports (early window is already visible) ───────────────────────────
import ctypes
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

import customtkinter as ctk
import keyboard
import pystray
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
from transcriber import Transcriber

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

# subprocess flag to hide console windows — only exists on Windows
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# ── Audio feedback ────────────────────────────────────────────────────────────

def _beep(frequency: int, duration_ms: int):
    if sys.platform == "win32":
        import winsound
        winsound.Beep(frequency, duration_ms)
    # Linux: silent — no reliable cross-desktop audio notification without extra deps


# ── Single instance ───────────────────────────────────────────────────────────
_mutex = None
_lock_file = None
_pynput_listener = None  # Linux only

def _ensure_single_instance():
    global _mutex, _lock_file
    if sys.platform == "win32":
        _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\MurmerSingleInstance")
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            sys.exit(0)
    else:
        import fcntl, tempfile
        lock_path = Path(tempfile.gettempdir()) / "murmer.lock"
        _lock_file = open(lock_path, "w")
        try:
            fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            sys.exit(0)


# ── State ─────────────────────────────────────────────────────────────────────
_recording = False
_processing = False
_icon: pystray.Icon | None = None
_root: ctk.CTk | None = None
_server_proc: subprocess.Popen | None = None

recorder = Recorder()
transcriber = Transcriber()
cleaner = None
overlay: RecordingOverlay | None = None
settings_win: SettingsWindow | None = None
log_win: LogWindow | None = None
server_manager_win: ServerManagerWindow | None = None


# ── Cleaner ───────────────────────────────────────────────────────────────────

def _load_cleaner():
    global cleaner
    cleaner = None
    if config.AI_CLEANUP_ENABLED and config.ANTHROPIC_API_KEY:
        from cleaner import Cleaner
        cleaner = Cleaner()
        logger.log("AI cleanup enabled (Claude Haiku).")
    else:
        logger.log("AI cleanup disabled.")


# ── Tray icon ─────────────────────────────────────────────────────────────────

def _make_icon(recording=False, processing=False) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    d.rounded_rectangle([1, 1, 62, 62], radius=14, fill="#1a1a1e")

    if recording:
        color = "#D94040"
    elif processing:
        color = "#D4A030"
    else:
        color = "#8A8A8E"

    heights = [10, 18, 28, 38, 28, 18, 10]
    bar_w, gap = 5, 3
    total_w = len(heights) * bar_w + (len(heights) - 1) * gap
    sx = (64 - total_w) // 2
    cy = 32

    for i, h in enumerate(heights):
        x = sx + i * (bar_w + gap)
        d.rounded_rectangle([x, cy - h // 2, x + bar_w - 1, cy + h // 2],
                            radius=2, fill=color)
    return img


def _update_icon():
    if _icon:
        _icon.icon = _make_icon(recording=_recording, processing=_processing)


# ── Recording ─────────────────────────────────────────────────────────────────

def _on_press():
    global _recording
    if _recording or _processing:
        return
    _recording = True
    _update_icon()
    _beep(880, 80)
    recorder.start()
    if config.SHOW_OVERLAY and overlay:
        overlay.show()


def _on_release():
    global _recording, _processing
    if not _recording:
        return
    audio = recorder.stop()
    _recording = False
    if overlay:
        overlay.hide()

    if audio is None or len(audio) < config.MIN_RECORDING_SAMPLES:
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
        text, language = transcriber.transcribe(audio)
        if not text:
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
    """Map keyboard-lib key string to a pynput Key constant, or return the string for char keys."""
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
        keyboard.unhook_all()
    else:
        if _pynput_listener is not None:
            _pynput_listener.stop()


# ── Settings & restart ────────────────────────────────────────────────────────

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
    logger.log("Whisper Server gestart op poort 8765.")
    if _icon:
        _icon.update_menu()


def _stop_whisper_server():
    global _server_proc
    if _server_proc and _server_proc.poll() is None:
        _server_proc.terminate()
        try:
            _server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_proc.kill()
    _server_proc = None
    # Kill any orphaned instances (e.g. manually started)
    if sys.platform == "win32":
        subprocess.run(
            ["powershell", "-Command",
             "Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like "
             "'*faster_whisper_server*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
            creationflags=_NO_WINDOW,
            capture_output=True,
        )
    else:
        subprocess.run(["pkill", "-f", "faster_whisper_server"], capture_output=True)
    logger.log("Whisper Server gestopt.")
    if _icon:
        _icon.update_menu()


def _open_settings():
    if _root and settings_win:
        _root.after(0, settings_win.open)


def _open_log():
    if _root and log_win:
        _root.after(0, log_win.open)


def _open_server_manager():
    if _root and server_manager_win:
        _root.after(0, server_manager_win.open)


def _on_settings_saved(updates: dict):
    _load_cleaner()
    if "PUSH_TO_TALK_KEY" in updates:
        _stop_hotkey_listener()
        threading.Thread(target=_keyboard_listener, daemon=True).start()
        logger.log(f"Hotkey updated to: {config.PUSH_TO_TALK_KEY}")
    logger.log("Settings saved.")


def _restart():
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
    _stop_hotkey_listener()
    if _icon:
        _icon.stop()
    if _root:
        _root.after(0, _do_restart)


def _do_restart():
    _root.quit()
    os.execv(sys.executable, [sys.executable] + sys.argv)


# ── Quit ──────────────────────────────────────────────────────────────────────

def _quit():
    _stop_hotkey_listener()
    if _server_running():
        _stop_whisper_server()
    if _icon:
        _icon.stop()
    if _root:
        _root.after(0, _root.quit)


# ── Startup ───────────────────────────────────────────────────────────────────

def _background_init(splash: SplashScreen):
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
    logger.log(f"Ready. Hold {key} to record, release to transcribe and paste.")

    menu = pystray.Menu(
        pystray.MenuItem("Murmer", None, enabled=False),
        pystray.MenuItem(f"Hold {key} to record", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Settings",      lambda icon, item: _open_settings()),
        pystray.MenuItem("Activity log",  lambda icon, item: _open_log()),
        pystray.MenuItem("Open history",  lambda icon, item: logger.open_history()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Whisper Server...", lambda icon, item: _open_server_manager()),
        pystray.MenuItem(
            lambda item: "● Server running" if _server_running() else "○ Server stopped",
            None, enabled=False,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Restart",       lambda icon, item: _restart()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", lambda icon, item: _quit()),
    )
    _icon = pystray.Icon("murmer", _make_icon(), "Murmer", menu)

    threading.Thread(target=_keyboard_listener, daemon=True).start()
    _icon.run_detached()

    _root.after(0, splash.hide)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    global _root, overlay, settings_win, log_win, server_manager_win, _early_win

    _ensure_single_instance()

    # Destroy early window before creating CTk root
    if _early_win:
        _early_win.destroy()
        _early_win = None

    _root = ctk.CTk()
    _root.withdraw()

    overlay = RecordingOverlay(_root)
    settings_win = SettingsWindow(_root, on_save=_on_settings_saved, on_restart=_restart)
    log_win = LogWindow(_root)
    server_manager_win = ServerManagerWindow(
        _root,
        get_server_running=_server_running,
        start_server=_start_whisper_server,
        stop_server=_stop_whisper_server,
    )

    splash = SplashScreen(_root)

    def _start():
        splash.show()
        threading.Thread(target=_background_init, args=(splash,), daemon=True).start()

    _root.after(100, _start)
    _root.mainloop()


if __name__ == "__main__":
    main()
