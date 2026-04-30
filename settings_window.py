import customtkinter as ctk

import autostart
import config


class SettingsWindow:
    def __init__(self, root: ctk.CTk, on_save=None):
        self._root = root
        self._on_save = on_save
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
        win.geometry("420x580")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.after(100, win.lift)
        self._win = win

        scroll = ctk.CTkScrollableFrame(win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(16, 4))

        # ── General ──────────────────────────────────────────────
        self._section(scroll, "GENERAL")

        self._label(scroll, "Push-to-talk key")
        self._hotkey_var = ctk.StringVar(value=config.PUSH_TO_TALK_KEY)
        ctk.CTkEntry(scroll, textvariable=self._hotkey_var, width=160,
                     placeholder_text="e.g. f9, right alt").pack(anchor="w", pady=(0, 14))

        self._autostart_var = ctk.BooleanVar(value=autostart.is_enabled())
        self._toggle_row(scroll, "Start with Windows", self._autostart_var)

        # ── Transcription ─────────────────────────────────────────
        self._section(scroll, "TRANSCRIPTION")

        self._label(scroll, "Model")
        self._model_var = ctk.StringVar(value=config.WHISPER_MODEL)
        ctk.CTkOptionMenu(scroll, values=["large-v3", "medium", "small", "base"],
                          variable=self._model_var, width=180).pack(anchor="w", pady=(0, 14))

        self._label(scroll, "Device")
        self._device_var = ctk.StringVar(value=config.WHISPER_DEVICE)
        ctk.CTkOptionMenu(scroll, values=["cuda", "cpu"],
                          variable=self._device_var, width=180).pack(anchor="w", pady=(0, 4))

        ctk.CTkLabel(scroll, text="⚠  Model and device changes require a restart.",
                     font=ctk.CTkFont(size=11), text_color="#777").pack(anchor="w", pady=(2, 14))

        # ── AI Cleanup ────────────────────────────────────────────
        self._section(scroll, "AI CLEANUP")

        self._cleanup_var = ctk.BooleanVar(value=config.AI_CLEANUP_ENABLED)
        self._toggle_row(scroll, "Enable AI cleanup (Claude Haiku)", self._cleanup_var)

        self._label(scroll, "Anthropic API key")
        self._apikey_var = ctk.StringVar(value=config.ANTHROPIC_API_KEY)
        ctk.CTkEntry(scroll, textvariable=self._apikey_var, show="●",
                     width=340, placeholder_text="sk-ant-...").pack(anchor="w", pady=(0, 14))

        # ── Display ───────────────────────────────────────────────
        self._section(scroll, "DISPLAY")

        self._overlay_var = ctk.BooleanVar(value=config.SHOW_OVERLAY)
        self._toggle_row(scroll, "Show recording overlay", self._overlay_var)

        # ── Save ──────────────────────────────────────────────────
        ctk.CTkButton(win, text="Save changes", command=self._save,
                      height=42, font=ctk.CTkFont(size=14)).pack(
            fill="x", padx=20, pady=(4, 16))

    # ── Helpers ───────────────────────────────────────────────────

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

    def _save(self):
        updates = {
            "PUSH_TO_TALK_KEY": self._hotkey_var.get().strip().lower() or "f9",
            "WHISPER_MODEL": self._model_var.get(),
            "WHISPER_DEVICE": self._device_var.get(),
            "WHISPER_COMPUTE_TYPE": "float16" if self._device_var.get() == "cuda" else "int8",
            "AI_CLEANUP_ENABLED": self._cleanup_var.get(),
            "ANTHROPIC_API_KEY": self._apikey_var.get().strip(),
            "SHOW_OVERLAY": self._overlay_var.get(),
            "AUTO_START": self._autostart_var.get(),
        }
        config.save(updates)
        autostart.set_enabled(self._autostart_var.get())
        if self._on_save:
            self._on_save(updates)
        self._win.destroy()
