import time
import tkinter as tk


class RecordingOverlay:
    def __init__(self, root: tk.Tk):
        self._root = root
        self._win: tk.Toplevel | None = None
        self._timer_id = None
        self._start_time = 0.0
        self._dot_on = True

    def show(self):
        self._start_time = time.time()
        self._root.after(0, self._create)

    def hide(self):
        self._root.after(0, self._destroy)

    def _create(self):
        if self._win and self._win.winfo_exists():
            return

        win = tk.Toplevel(self._root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.90)
        win.configure(bg="#1c1c1e")

        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        w, h = 210, 52
        win.geometry(f"{w}x{h}+{sw - w - 20}+{sh - h - 72}")

        # Rounded feel via inner frame
        frame = tk.Frame(win, bg="#1c1c1e", padx=14, pady=12)
        frame.pack(fill="both", expand=True)

        self._dot = tk.Label(frame, text="●", fg="#ff3b30", bg="#1c1c1e",
                             font=("Segoe UI", 13))
        self._dot.pack(side="left", padx=(0, 8))

        self._label = tk.Label(frame, text="Recording  0:00", fg="#f0f0f0",
                               bg="#1c1c1e", font=("Segoe UI", 12))
        self._label.pack(side="left")

        self._win = win
        self._tick()

    def _tick(self):
        if not self._win or not self._win.winfo_exists():
            return
        elapsed = int(time.time() - self._start_time)
        m, s = divmod(elapsed, 60)
        self._label.config(text=f"Recording  {m}:{s:02d}")
        self._dot_on = not self._dot_on
        self._dot.config(fg="#ff3b30" if self._dot_on else "#7a2020")
        self._timer_id = self._win.after(500, self._tick)

    def _destroy(self):
        if self._win and self._win.winfo_exists():
            if self._timer_id:
                try:
                    self._win.after_cancel(self._timer_id)
                except Exception:
                    pass
            self._win.destroy()
        self._win = None
        self._timer_id = None
