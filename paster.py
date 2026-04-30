import time
import pyperclip
import keyboard


def paste_text(text: str):
    previous = pyperclip.paste()
    pyperclip.copy(text)
    time.sleep(0.05)  # Let clipboard settle
    keyboard.send("ctrl+v")
    time.sleep(0.1)
    try:
        pyperclip.copy(previous)
    except Exception:
        pass
