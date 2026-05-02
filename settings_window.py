import threading

import customtkinter as ctk
import keyboard

import autostart
import config
from recorder import device_available, get_device_names


def _parse_corrections(text: str) -> dict:
    result = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if "=" in line:
            wrong, right = line.split("=", 1)
            wrong, right = wrong.strip(), right.strip()
            if wrong and right:
                result[wrong] = right
    return result


def _corrections_to_text(d: dict) -> str:
    return "\n".join(f"{k}={v}" for k, v in d.items())


_NAV_ITEMS = ["General", "Audio", "Transcription", "AI Cleanup", "Display", "Profile"]


class SettingsWindow:
    def __init__(self, root: ctk.CTk, on_save=None, on_restart=None):
        self._root = root
        self._on_save = on_save
        self._on_restart = on_restart
        self._win: ctk.CTkToplevel | None = None
        self._section_frames: dict[str, ctk.CTkScrollableFrame] = {}
        self._nav_buttons: dict[str, ctk.CTkButton] = {}

    def open(self):
        if self._win and self._win.winfo_exists():
            self._win.lift()
            self._win.focus()
            return
        self._build()

    # ── Layout skeleton ───────────────────────────────────────────

    def _build(self):
        win = ctk.CTkToplevel(self._root)
        win.title("Murmer — Settings")
        win.geometry("720x500")
        win.minsize(600, 420)
        win.resizable(True, True)
        win.attributes("-topmost", True)
        win.after(100, win.lift)
        self._win = win

        # ── Bottom bar (pack first → always visible) ──────────────
        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", padx=16, pady=(4, 16))
        ctk.CTkButton(btn_frame, text="Save changes", command=self._save,
                      height=40, font=ctk.CTkFont(size=14)).pack(
            side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(btn_frame, text="Save & Restart", command=self._save_and_restart,
                      height=40, font=ctk.CTkFont(size=14),
                      fg_color="#555", hover_color="#444").pack(
            side="left", expand=True, fill="x", padx=(6, 0))

        # ── Main area ─────────────────────────────────────────────
        main = ctk.CTkFrame(win, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=16, pady=(16, 4))

        # Sidebar
        sidebar = ctk.CTkFrame(main, width=148, corner_radius=10)
        sidebar.pack(side="left", fill="y", padx=(0, 12))
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text="Settings",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#555").pack(anchor="w", padx=14, pady=(14, 8))

        for name in _NAV_ITEMS:
            btn = ctk.CTkButton(
                sidebar, text=name,
                anchor="w",
                height=34,
                corner_radius=6,
                fg_color="transparent",
                hover_color=("#3a3a3c", "#3a3a3c"),
                text_color=("#ebebeb", "#ebebeb"),
                font=ctk.CTkFont(size=13),
                command=lambda n=name: self._show_section(n),
            )
            btn.pack(fill="x", padx=8, pady=2)
            self._nav_buttons[name] = btn

        # Content area
        self._content_area = ctk.CTkFrame(main, corner_radius=10)
        self._content_area.pack(side="left", fill="both", expand=True)
        self._content_area.grid_rowconfigure(0, weight=1)
        self._content_area.grid_columnconfigure(0, weight=1)

        # Build all section frames
        self._build_general()
        self._build_audio()
        self._build_transcription()
        self._build_ai_cleanup()
        self._build_display()
        self._build_profile()

        self._show_section("General")

    def _show_section(self, name: str):
        for frame in self._section_frames.values():
            frame.grid_remove()
        for btn_name, btn in self._nav_buttons.items():
            btn.configure(fg_color="transparent",
                          text_color=("#ebebeb", "#ebebeb"),
                          font=ctk.CTkFont(size=13))
        self._section_frames[name].grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self._nav_buttons[name].configure(
            fg_color=("#1f538d", "#1f538d"),
            text_color=("#ffffff", "#ffffff"),
            font=ctk.CTkFont(size=13, weight="bold"),
        )

    def _make_section(self, name: str) -> ctk.CTkScrollableFrame:
        frame = ctk.CTkScrollableFrame(self._content_area, fg_color="transparent")
        self._section_frames[name] = frame
        return frame

    # ── Section: General ──────────────────────────────────────────

    def _build_general(self):
        f = self._make_section("General")
        self._page_title(f, "General")

        self._label(f, "Push-to-talk key")
        self._hotkey_var = ctk.StringVar(value=config.PUSH_TO_TALK_KEY)
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(anchor="w", pady=(0, 20))
        self._hotkey_entry = ctk.CTkEntry(row, textvariable=self._hotkey_var,
                                          width=120, state="readonly")
        self._hotkey_entry.pack(side="left", padx=(0, 8))
        self._capture_btn = ctk.CTkButton(row, text="Capture key", width=110,
                                          command=self._start_capture)
        self._capture_btn.pack(side="left")

        self._autostart_var = ctk.BooleanVar(value=autostart.is_enabled())
        self._toggle_row(f, "Start with System", self._autostart_var)

    # ── Section: Audio ────────────────────────────────────────────

    def _build_audio(self):
        f = self._make_section("Audio")
        self._page_title(f, "Audio")

        self._label(f, "Input device")
        device_names = get_device_names()
        current_device = config.AUDIO_DEVICE if config.AUDIO_DEVICE else "Default"
        if current_device not in device_names:
            device_names.append(current_device)
        self._device_input_var = ctk.StringVar(value=current_device)
        ctk.CTkOptionMenu(f, values=device_names,
                          variable=self._device_input_var,
                          width=320).pack(anchor="w", pady=(0, 6))
        available = device_available(config.AUDIO_DEVICE)
        status_text = "✓  Device available" if available else "⚠  Device not detected"
        status_color = "#4CAF50" if available else "#E07B39"
        ctk.CTkLabel(f, text=status_text, font=ctk.CTkFont(size=11),
                     text_color=status_color).pack(anchor="w", pady=(0, 14))

    # ── Section: Transcription ────────────────────────────────────

    def _build_transcription(self):
        f = self._make_section("Transcription")
        self._page_title(f, "Transcription")

        self._label(f, "Mode")
        self._mode_var = ctk.StringVar(value=config.TRANSCRIPTION_MODE)
        ctk.CTkSegmentedButton(f, values=["local", "remote"],
                               variable=self._mode_var, width=180,
                               command=self._on_mode_change).pack(anchor="w", pady=(0, 16))

        self._mode_container = ctk.CTkFrame(f, fg_color="transparent")
        self._mode_container.pack(anchor="w", fill="x")

        # Local fields
        self._local_frame = ctk.CTkFrame(self._mode_container, fg_color="transparent")
        self._label(self._local_frame, "Model")
        self._model_var = ctk.StringVar(value=config.WHISPER_MODEL)
        ctk.CTkOptionMenu(self._local_frame,
                          values=["large-v3", "medium", "small", "base"],
                          variable=self._model_var, width=180).pack(anchor="w", pady=(0, 16))
        self._label(self._local_frame, "Device")
        self._device_var = ctk.StringVar(value=config.WHISPER_DEVICE)
        ctk.CTkOptionMenu(self._local_frame, values=["cuda", "cpu"],
                          variable=self._device_var, width=180).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(self._local_frame,
                     text="⚠  Model and device changes require a restart.",
                     font=ctk.CTkFont(size=11), text_color="#777").pack(anchor="w", pady=(2, 14))

        # Remote fields
        self._remote_frame = ctk.CTkFrame(self._mode_container, fg_color="transparent")

        # Saved servers row
        self._label(self._remote_frame, "Saved servers")
        saved_row = ctk.CTkFrame(self._remote_frame, fg_color="transparent")
        saved_row.pack(anchor="w", fill="x", pady=(0, 16))

        self._saved_server_var = ctk.StringVar(value=self._saved_server_placeholder())
        self._saved_server_menu = ctk.CTkOptionMenu(
            saved_row,
            values=self._saved_server_options(),
            variable=self._saved_server_var,
            command=self._on_server_selected,
            width=300,
        )
        self._saved_server_menu.pack(side="left", padx=(0, 8))
        self._delete_btn = ctk.CTkButton(
            saved_row, text="Delete", width=70, height=32,
            fg_color="#8B2020", hover_color="#6B1818",
            font=ctk.CTkFont(size=12),
            command=self._delete_saved_server,
        )
        self._delete_btn.pack(side="left")
        self._refresh_delete_btn()

        # URL + key fields
        self._label(self._remote_frame, "Server URL")
        self._remote_url_var = ctk.StringVar(value=config.REMOTE_WHISPER_URL)
        ctk.CTkEntry(self._remote_frame, textvariable=self._remote_url_var,
                     width=420, placeholder_text="http://100.x.x.x:8765").pack(anchor="w", pady=(0, 16))
        self._label(self._remote_frame, "API key")
        self._remote_key_var = ctk.StringVar(value=config.REMOTE_WHISPER_API_KEY)
        ctk.CTkEntry(self._remote_frame, textvariable=self._remote_key_var,
                     show="●", width=420, placeholder_text="your API key").pack(anchor="w", pady=(0, 12))

        # Save current button
        ctk.CTkButton(
            self._remote_frame, text="Save current as...", width=160, height=32,
            font=ctk.CTkFont(size=12),
            fg_color="#2d5a2d", hover_color="#1e3d1e",
            command=self._save_server_as,
        ).pack(anchor="w", pady=(0, 14))

        self._on_mode_change(self._mode_var.get())

    # ── Saved servers helpers ─────────────────────────────────────

    def _saved_server_placeholder(self) -> str:
        return "— select a saved server —"

    def _saved_server_options(self) -> list[str]:
        names = [s["name"] for s in config.SAVED_SERVERS]
        return names if names else [self._saved_server_placeholder()]

    def _refresh_server_menu(self):
        options = self._saved_server_options()
        self._saved_server_menu.configure(values=options)
        if self._saved_server_var.get() not in options:
            self._saved_server_var.set(self._saved_server_placeholder())
        self._refresh_delete_btn()

    def _refresh_delete_btn(self):
        placeholder = self._saved_server_placeholder()
        is_real = (self._saved_server_var.get() != placeholder
                   and bool(config.SAVED_SERVERS))
        self._delete_btn.configure(state="normal" if is_real else "disabled")

    def _on_server_selected(self, name: str):
        if name == self._saved_server_placeholder():
            return
        for server in config.SAVED_SERVERS:
            if server["name"] == name:
                self._remote_url_var.set(server["url"])
                self._remote_key_var.set(server["api_key"])
                break
        self._refresh_delete_btn()

    def _save_server_as(self):
        url = self._remote_url_var.get().strip()
        key = self._remote_key_var.get().strip()
        if not url:
            return
        dialog = ctk.CTkInputDialog(
            text="Enter a name for this server:",
            title="Save server",
        )
        name = dialog.get_input()
        if not name or not name.strip():
            return
        name = name.strip()
        servers = list(config.SAVED_SERVERS)
        # Overwrite if name already exists
        servers = [s for s in servers if s["name"] != name]
        servers.append({"name": name, "url": url, "api_key": key})
        config.save({"SAVED_SERVERS": servers})
        self._saved_server_var.set(name)
        self._refresh_server_menu()

    def _delete_saved_server(self):
        name = self._saved_server_var.get()
        if name == self._saved_server_placeholder():
            return
        servers = [s for s in config.SAVED_SERVERS if s["name"] != name]
        config.save({"SAVED_SERVERS": servers})
        self._refresh_server_menu()

    # ── Section: AI Cleanup ───────────────────────────────────────

    def _build_ai_cleanup(self):
        f = self._make_section("AI Cleanup")
        self._page_title(f, "AI Cleanup")

        self._cleanup_var = ctk.BooleanVar(value=config.AI_CLEANUP_ENABLED)
        self._toggle_row(f, "Enable AI cleanup (Claude Haiku)", self._cleanup_var)

        self._label(f, "Anthropic API key")
        self._apikey_var = ctk.StringVar(value=config.ANTHROPIC_API_KEY)
        ctk.CTkEntry(f, textvariable=self._apikey_var, show="●",
                     width=420, placeholder_text="sk-ant-...").pack(anchor="w", pady=(0, 14))

    # ── Section: Display ──────────────────────────────────────────

    def _build_display(self):
        f = self._make_section("Display")
        self._page_title(f, "Display")

        self._overlay_var = ctk.BooleanVar(value=config.SHOW_OVERLAY)
        self._toggle_row(f, "Show recording overlay", self._overlay_var)

    # ── Section: Profile ──────────────────────────────────────────

    def _build_profile(self):
        f = self._make_section("Profile")
        self._page_title(f, "Profile")

        self._label(f, "Transcription style")
        self._style_var = ctk.StringVar(value=config.TRANSCRIPTION_STYLE)
        ctk.CTkOptionMenu(f, values=["none", "formal", "informal", "technical", "custom"],
                          variable=self._style_var, width=180,
                          command=self._on_style_change).pack(anchor="w", pady=(0, 12))

        # Custom style box — created but not packed yet
        self._custom_style_frame = ctk.CTkFrame(f, fg_color="transparent")
        self._label(self._custom_style_frame, "Custom style instructions")
        self._custom_style_box = ctk.CTkTextbox(self._custom_style_frame, height=68,
                                                 wrap="word", font=ctk.CTkFont(size=12))
        self._custom_style_box.pack(fill="x", pady=(0, 12))
        if config.CUSTOM_STYLE_PROMPT:
            self._custom_style_box.insert("1.0", config.CUSTOM_STYLE_PROMPT)

        # "About you" label stored as reference for before= positioning
        self._about_label = ctk.CTkLabel(f, text="About you  (Haiku uses this as context)",
                                          font=ctk.CTkFont(size=13))
        self._about_label.pack(anchor="w", pady=(0, 4))
        self._profile_box = ctk.CTkTextbox(f, height=68, wrap="word",
                                            font=ctk.CTkFont(size=12))
        self._profile_box.pack(fill="x", pady=(0, 4))
        if config.USER_PROFILE:
            self._profile_box.insert("1.0", config.USER_PROFILE)
        ctk.CTkLabel(f, text='Example: "I\'m a developer. I often say \'PR\', \'repo\', \'deploy\'."',
                     font=ctk.CTkFont(size=11), text_color="#555").pack(anchor="w", pady=(0, 16))

        self._label(f, "Word corrections")
        self._corrections_box = ctk.CTkTextbox(f, height=88, wrap="none",
                                                font=ctk.CTkFont(family="Consolas", size=12))
        self._corrections_box.pack(fill="x", pady=(0, 4))
        if config.WORD_CORRECTIONS:
            self._corrections_box.insert("1.0", _corrections_to_text(config.WORD_CORRECTIONS))
        ctk.CTkLabel(f, text="One correction per line:  wrong=Right  (also applied without AI cleanup)",
                     font=ctk.CTkFont(size=11), text_color="#555").pack(anchor="w", pady=(0, 14))

        self._on_style_change(self._style_var.get())

    # ── Helpers ───────────────────────────────────────────────────

    def _page_title(self, parent, text: str):
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(4, 18))

    def _label(self, parent, text: str):
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(0, 4))

    def _toggle_row(self, parent, label: str, var: ctk.BooleanVar):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=13)).pack(side="left")
        ctk.CTkSwitch(row, text="", variable=var, width=52).pack(side="right")

    def _on_style_change(self, value: str):
        if value == "custom":
            self._custom_style_frame.pack(anchor="w", fill="x",
                                           before=self._about_label)
        else:
            self._custom_style_frame.pack_forget()

    def _on_mode_change(self, value: str):
        if value == "local":
            self._remote_frame.pack_forget()
            self._local_frame.pack(anchor="w", fill="x")
        else:
            self._local_frame.pack_forget()
            self._remote_frame.pack(anchor="w", fill="x")

    def _start_capture(self):
        self._capture_btn.configure(text="Press a key...", state="disabled")
        self._hotkey_var.set("...")
        threading.Thread(target=self._capture_key, daemon=True).start()

    def _capture_key(self):
        import sys
        if sys.platform == "win32":
            key = keyboard.read_key(suppress=True)
        else:
            from pynput import keyboard as _pk
            captured = [None]

            def on_press(k):
                try:
                    captured[0] = k.name if hasattr(k, 'name') else k.char
                except AttributeError:
                    captured[0] = str(k)
                return False  # stop listener after first key

            with _pk.Listener(on_press=on_press) as _listener:
                _listener.join()
            key = captured[0] or "f9"
        self._win.after(0, lambda: self._hotkey_var.set(key))
        self._win.after(0, lambda: self._capture_btn.configure(
            text="Capture key", state="normal"))

    # ── Collect & save ────────────────────────────────────────────

    def _collect_updates(self) -> dict:
        mode = self._mode_var.get()
        selected_device = self._device_input_var.get()
        updates = {
            "PUSH_TO_TALK_KEY":       self._hotkey_var.get().strip().lower() or "f9",
            "AUDIO_DEVICE":           None if selected_device == "Default" else selected_device,
            "TRANSCRIPTION_MODE":     mode,
            "REMOTE_WHISPER_URL":     self._remote_url_var.get().strip(),
            "REMOTE_WHISPER_API_KEY": self._remote_key_var.get().strip(),
            "AI_CLEANUP_ENABLED":     self._cleanup_var.get(),
            "ANTHROPIC_API_KEY":      self._apikey_var.get().strip(),
            "SHOW_OVERLAY":           self._overlay_var.get(),
            "AUTO_START":             self._autostart_var.get(),
            "TRANSCRIPTION_STYLE":    self._style_var.get(),
            "CUSTOM_STYLE_PROMPT":    self._custom_style_box.get("1.0", "end-1c").strip(),
            "USER_PROFILE":           self._profile_box.get("1.0", "end-1c").strip(),
            "WORD_CORRECTIONS":       _parse_corrections(
                                          self._corrections_box.get("1.0", "end-1c")),
        }
        if mode == "local":
            updates["WHISPER_MODEL"]        = self._model_var.get()
            updates["WHISPER_DEVICE"]       = self._device_var.get()
            updates["WHISPER_COMPUTE_TYPE"] = (
                "float16" if self._device_var.get() == "cuda" else "int8")
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
