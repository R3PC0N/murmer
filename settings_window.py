import threading

import customtkinter as ctk
import keyboard

import autostart
import config


class SettingsWindow:
    def __init__(self, root: ctk.CTk, on_save=None, on_restart=None):
        self._root = root
        self._on_save = on_save
        self._on_restart = on_restart
        self._win: ctk.CTkToplevel | None = None

    def open(self):
        if self._win and self._win.winfo_exists():
            self._win.lift()
            self._win.focus()
            return
        self._build()

    def _build(self):
        win = ctk.CTkToplevel(self._root)
        win.title("Murmer — Settings")
        win.geometry("460x780")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.after(100, win.lift)
        self._win = win

        # Knoppen eerst packen zodat ze altijd op vaste positie onderin staan
        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", padx=24, pady=(4, 20))

        ctk.CTkButton(btn_frame, text="Save changes", command=self._save,
                      height=42, font=ctk.CTkFont(size=14)).pack(
            side="left", expand=True, fill="x", padx=(0, 6))

        ctk.CTkButton(btn_frame, text="Save & Restart", command=self._save_and_restart,
                      height=42, font=ctk.CTkFont(size=14),
                      fg_color="#555", hover_color="#444").pack(
            side="left", expand=True, fill="x", padx=(6, 0))

        content = ctk.CTkFrame(win, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=(16, 4))

        # ── General ──────────────────────────────────────────────
        self._section(content, "GENERAL")

        self._label(content, "Push-to-talk key")
        self._hotkey_var = ctk.StringVar(value=config.PUSH_TO_TALK_KEY)
        hotkey_row = ctk.CTkFrame(content, fg_color="transparent")
        hotkey_row.pack(anchor="w", pady=(0, 14))
        self._hotkey_entry = ctk.CTkEntry(hotkey_row, textvariable=self._hotkey_var,
                                          width=140, state="readonly")
        self._hotkey_entry.pack(side="left", padx=(0, 8))
        self._capture_btn = ctk.CTkButton(hotkey_row, text="Capture key", width=110,
                                          command=self._start_capture)
        self._capture_btn.pack(side="left")

        self._autostart_var = ctk.BooleanVar(value=autostart.is_enabled())
        self._toggle_row(content, "Start with Windows", self._autostart_var)

        # ── Transcription ─────────────────────────────────────────
        self._section(content, "TRANSCRIPTION")

        self._label(content, "Mode")
        self._mode_var = ctk.StringVar(value=config.TRANSCRIPTION_MODE)
        mode_seg = ctk.CTkSegmentedButton(
            content,
            values=["local", "remote"],
            variable=self._mode_var,
            width=180,
            command=self._on_mode_change,
        )
        mode_seg.pack(anchor="w", pady=(0, 14))

        # Container op vaste positie — local en remote frames wisselen hierin
        self._mode_container = ctk.CTkFrame(content, fg_color="transparent")
        self._mode_container.pack(anchor="w", fill="x")

        # Local fields
        self._local_frame = ctk.CTkFrame(self._mode_container, fg_color="transparent")
        self._label(self._local_frame, "Model")
        self._model_var = ctk.StringVar(value=config.WHISPER_MODEL)
        ctk.CTkOptionMenu(self._local_frame, values=["large-v3", "medium", "small", "base"],
                          variable=self._model_var, width=180).pack(anchor="w", pady=(0, 14))
        self._label(self._local_frame, "Device")
        self._device_var = ctk.StringVar(value=config.WHISPER_DEVICE)
        ctk.CTkOptionMenu(self._local_frame, values=["cuda", "cpu"],
                          variable=self._device_var, width=180).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(self._local_frame, text="⚠  Model and device changes require a restart.",
                     font=ctk.CTkFont(size=11), text_color="#777").pack(anchor="w", pady=(2, 14))

        # Remote fields
        self._remote_frame = ctk.CTkFrame(self._mode_container, fg_color="transparent")
        self._label(self._remote_frame, "Server URL")
        self._remote_url_var = ctk.StringVar(value=config.REMOTE_WHISPER_URL)
        ctk.CTkEntry(self._remote_frame, textvariable=self._remote_url_var,
                     width=380, placeholder_text="http://100.x.x.x:8765").pack(anchor="w", pady=(0, 14))
        self._label(self._remote_frame, "Server API key")
        self._remote_key_var = ctk.StringVar(value=config.REMOTE_WHISPER_API_KEY)
        ctk.CTkEntry(self._remote_frame, textvariable=self._remote_key_var,
                     show="●", width=380, placeholder_text="jouw API key").pack(anchor="w", pady=(0, 14))

        # Toon correct frame
        self._on_mode_change(self._mode_var.get())

        # ── AI Cleanup ────────────────────────────────────────────
        self._section(content, "AI CLEANUP")

        self._cleanup_var = ctk.BooleanVar(value=config.AI_CLEANUP_ENABLED)
        self._toggle_row(content, "Enable AI cleanup (Claude Haiku)", self._cleanup_var)

        self._label(content, "Anthropic API key")
        self._apikey_var = ctk.StringVar(value=config.ANTHROPIC_API_KEY)
        ctk.CTkEntry(content, textvariable=self._apikey_var, show="●",
                     width=380, placeholder_text="sk-ant-...").pack(anchor="w", pady=(0, 14))

        # ── Display ───────────────────────────────────────────────
        self._section(content, "DISPLAY")

        self._overlay_var = ctk.BooleanVar(value=config.SHOW_OVERLAY)
        self._toggle_row(content, "Show recording overlay", self._overlay_var)


    # ── Helpers ───────────────────────────────────────────────────

    def _on_mode_change(self, value: str):
        if value == "local":
            self._remote_frame.pack_forget()
            self._local_frame.pack(anchor="w", fill="x")
        else:
            self._local_frame.pack_forget()
            self._remote_frame.pack(anchor="w", fill="x")


    def _section(self, parent, title: str):
        ctk.CTkLabel(parent, text=title,
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#666").pack(anchor="w", pady=(10, 4))

    def _label(self, parent, text: str):
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(0, 4))

    def _toggle_row(self, parent, label: str, var: ctk.BooleanVar):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=13)).pack(side="left")
        ctk.CTkSwitch(row, text="", variable=var, width=52).pack(side="right")

    def _start_capture(self):
        self._capture_btn.configure(text="Press a key...", state="disabled")
        self._hotkey_var.set("...")
        threading.Thread(target=self._capture_key, daemon=True).start()

    def _capture_key(self):
        key = keyboard.read_key(suppress=True)
        self._win.after(0, lambda: self._hotkey_var.set(key))
        self._win.after(0, lambda: self._capture_btn.configure(
            text="Capture key", state="normal"))

    def _collect_updates(self) -> dict:
        mode = self._mode_var.get()
        updates = {
            "PUSH_TO_TALK_KEY": self._hotkey_var.get().strip().lower() or "f9",
            "TRANSCRIPTION_MODE": mode,
            "REMOTE_WHISPER_URL": self._remote_url_var.get().strip(),
            "REMOTE_WHISPER_API_KEY": self._remote_key_var.get().strip(),
            "AI_CLEANUP_ENABLED": self._cleanup_var.get(),
            "ANTHROPIC_API_KEY": self._apikey_var.get().strip(),
            "SHOW_OVERLAY": self._overlay_var.get(),
            "AUTO_START": self._autostart_var.get(),
        }
        if mode == "local":
            updates["WHISPER_MODEL"] = self._model_var.get()
            updates["WHISPER_DEVICE"] = self._device_var.get()
            updates["WHISPER_COMPUTE_TYPE"] = "float16" if self._device_var.get() == "cuda" else "int8"
        return updates

    def _save(self):
        updates = self._collect_updates()
        config.save(updates)
        autostart.set_enabled(self._autostart_var.get())
        if self._on_save:
            self._on_save(updates)
        self._win.destroy()

    def _save_and_restart(self):
        updates = self._collect_updates()
        config.save(updates)
        autostart.set_enabled(self._autostart_var.get())
        if self._on_save:
            self._on_save(updates)
        self._win.destroy()
        if self._on_restart:
            self._on_restart()
