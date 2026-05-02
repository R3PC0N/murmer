import subprocess
import sys
import time

import pyperclip


def paste_text(text: str):
    if sys.platform == "win32":
        previous = pyperclip.paste()
        pyperclip.copy(text)
        time.sleep(0.05)
        import keyboard
        keyboard.send("ctrl+v")
        time.sleep(0.1)
        try:
            pyperclip.copy(previous)
        except Exception:
            pass
    else:
        # xdotool type works in all X11 windows including terminals,
        # unlike ctrl+v which fails in terminals (they need ctrl+shift+v).
        subprocess.run(
            ["xdotool", "type", "--clearmodifiers", "--delay", "0", "--", text],
            check=False,
        )
