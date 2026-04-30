import threading
import winsound

import customtkinter as ctk
import keyboard
import pystray
from PIL import Image, ImageDraw

import config
from overlay import RecordingOverlay
from paster import paste_text
from recorder import Recorder
from settings_window import SettingsWindow
from transcriber import Transcriber

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ── State ─────────────────────────────────────────────────────────────────────
_recording = False
_processing = False
_icon: pystray.Icon | None = None
_root: ctk.CTk | None = None

recorder = Recorder()
transcriber = Transcriber()
cleaner = None
overlay: RecordingOverlay | None = None
settings_win: SettingsWindow | None = None


# ── Cleaner ───────────────────────────────────────────────────────────────────

def _load_cleaner():
    global cleaner
    cleaner = None
    if config.AI_CLEANUP_ENABLED and config.ANTHROPIC_API_KEY:
        from cleaner import Cleaner
        cleaner = Cleaner()
        print("AI cleanup enabled (Claude Haiku).")
    else:
        print("AI cleanup disabled.")


# ── Tray icon ─────────────────────────────────────────────────────────────────

def _make_icon(recording=False, processing=False) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if recording:
        bg = (210, 45, 45)
    elif processing:
        bg = (210, 165, 30)
    else:
        bg = (45, 170, 90)
    d.ellipse([2, 2, 62, 62], fill=bg)
    d.rounded_rectangle([23, 10, 41, 38], radius=9, fill="white")
    d.rectangle([30, 37, 34, 50], fill="white")
    d.ellipse([22, 49, 42, 55], fill="white")
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
    winsound.Beep(880, 80)
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


def _process(audio):
    global _processing
    try:
        text, language = transcriber.transcribe(audio)
        if not text:
            return
        print(f"Transcribed ({language}): {text}")
        if cleaner and config.AI_CLEANUP_ENABLED:
            text = cleaner.clean(text, language)
            print(f"Cleaned:               {text}")
        paste_text(text)
        winsound.Beep(660, 80)
    except Exception as e:
        print(f"Error: {e}")
        winsound.Beep(300, 250)
    finally:
        _processing = False
        _update_icon()


# ── Hotkey listener ───────────────────────────────────────────────────────────

def _keyboard_listener():
    _held = False

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


# ── Settings ──────────────────────────────────────────────────────────────────

def _open_settings():
    if _root and settings_win:
        _root.after(0, settings_win.open)


def _on_settings_saved(updates: dict):
    _load_cleaner()
    print("Settings saved.")


# ── Quit ──────────────────────────────────────────────────────────────────────

def _quit():
    keyboard.unhook_all()
    if _icon:
        _icon.stop()
    if _root:
        _root.after(0, _root.quit)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    global _icon, _root, overlay, settings_win

    _root = ctk.CTk()
    _root.withdraw()

    transcriber.load()
    _load_cleaner()

    overlay = RecordingOverlay(_root)
    settings_win = SettingsWindow(_root, on_save=_on_settings_saved)

    key = config.PUSH_TO_TALK_KEY.upper()
    print(f"Ready. Hold {key} to record, release to transcribe and paste.")

    menu = pystray.Menu(
        pystray.MenuItem("Murmer", None, enabled=False),
        pystray.MenuItem(f"Hold {key} to record", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Settings", lambda icon, item: _open_settings()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", lambda icon, item: _quit()),
    )
    _icon = pystray.Icon("murmer", _make_icon(), "Murmer", menu)

    threading.Thread(target=_keyboard_listener, daemon=True).start()
    _icon.run_detached()

    _root.mainloop()


if __name__ == "__main__":
    main()
