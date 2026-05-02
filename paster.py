import subprocess
import sys
import time

import pyperclip


def paste_text(text: str):
    previous = pyperclip.paste()
    pyperclip.copy(text)
    time.sleep(0.05)  # Let clipboard settle

    if sys.platform == "win32":
        import keyboard
        keyboard.send("ctrl+v")
    else:
        subprocess.run(["xdotool", "key", "--clearmodifiers", "ctrl+v"], check=False)

    time.sleep(0.1)
    try:
        pyperclip.copy(previous)
    except Exception:
        pass
