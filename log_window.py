import customtkinter as ctk

import logger


class LogWindow:
    def __init__(self, root: ctk.CTk):
        self._root = root
        self._win: ctk.CTkToplevel | None = None
        self._mode = ctk.StringVar(value="compact")

    def open(self):
        if self._win and self._win.winfo_exists():
            self._win.lift()
            self._win.focus()
            return
        self._build()

    def _build(self):
        win = ctk.CTkToplevel(self._root)
        win.title("Murmur — Activity")
        win.geometry("580x420")
        win.protocol("WM_DELETE_WINDOW", self._on_close)
        win.after(100, win.lift)
        self._win = win

        # Header
        header = ctk.CTkFrame(win, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 0))

        ctk.CTkLabel(header, text="Activity",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")

        ctk.CTkSegmentedButton(
            header,
            values=["compact", "debug"],
            variable=self._mode,
            width=160,
            command=self._refresh,
        ).pack(side="right")

        # Log text area
        self._text = ctk.CTkTextbox(
            win, wrap="word",
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self._text.pack(fill="both", expand=True, padx=16, pady=10)
        self._text.configure(state="disabled")

        # Footer
        footer = ctk.CTkFrame(win, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkButton(footer, text="Open history", width=130,
                      command=logger.open_history).pack(side="left")

        ctk.CTkButton(footer, text="Clear", width=80,
                      fg_color="#444", hover_color="#555",
                      command=self._clear).pack(side="right")

        self._refresh()
        logger.add_callback(self._on_new_entry)

    def _on_close(self):
        logger.remove_callback(self._on_new_entry)
        if self._win:
            self._win.destroy()
        self._win = None

    def _on_new_entry(self, entry):
        if self._win and self._win.winfo_exists():
            self._win.after(0, lambda e=entry: self._append(e))

    def _should_show(self, level: str) -> bool:
        if self._mode.get() == "debug":
            return True
        return level in ("RESULT", "ERROR")

    def _append(self, entry: tuple[str, str, str]):
        ts, level, message = entry
        if not self._should_show(level):
            return
        self._text.configure(state="normal")
        prefix = f"[{ts}] "
        if level == "ERROR":
            prefix += "⚠ "
        self._text.insert("end", prefix + message + "\n")
        self._text.see("end")
        self._text.configure(state="disabled")

    def _refresh(self, *_):
        if not self._win or not self._win.winfo_exists():
            return
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        for entry in logger.get_buffer():
            ts, level, message = entry
            if self._should_show(level):
                prefix = f"[{ts}] "
                if level == "ERROR":
                    prefix += "⚠ "
                self._text.insert("end", prefix + message + "\n")
        self._text.see("end")
        self._text.configure(state="disabled")

    def _clear(self):
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")
