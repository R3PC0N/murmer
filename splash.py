import customtkinter as ctk


class SplashScreen:
    def __init__(self, root: ctk.CTk):
        self._root = root
        self._win: ctk.CTkToplevel | None = None

    def show(self):
        win = ctk.CTkToplevel(self._root)
        win.title("")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.protocol("WM_DELETE_WINDOW", lambda: None)  # Prevent manual close

        w, h = 320, 188
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        ctk.CTkLabel(win, text="Murmur",
                     font=ctk.CTkFont(size=28, weight="bold")).pack(pady=(28, 6))
        ctk.CTkLabel(win, text="Loading speech model...",
                     font=ctk.CTkFont(size=13),
                     text_color="#888").pack()

        bar = ctk.CTkProgressBar(win, mode="indeterminate", width=240)
        bar.pack(pady=(16, 8))
        bar.start()

        ctk.CTkLabel(win, text="First launch may take a minute.",
                     font=ctk.CTkFont(size=11),
                     text_color="#555").pack()

        self._win = win

    def hide(self):
        if self._win and self._win.winfo_exists():
            self._win.destroy()
        self._win = None
