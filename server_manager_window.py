import subprocess
import sys
import threading
from pathlib import Path

import customtkinter as ctk

import config
import logger

_SERVER_DIR = Path(__file__).parent / "server"
_VENV_PYTHON = _SERVER_DIR / "venv" / ("Scripts" if sys.platform == "win32" else "bin") / (
    "python.exe" if sys.platform == "win32" else "python"
)
_SERVER_SCRIPT = _SERVER_DIR / "faster_whisper_server.py"
_REQUIREMENTS = _SERVER_DIR / "requirements.txt"
_ENV_FILE = _SERVER_DIR / ".env"
_ENV_EXAMPLE = _SERVER_DIR / ".env.example"

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _is_installed() -> bool:
    return _VENV_PYTHON.exists() and _SERVER_SCRIPT.exists()


def _open_firewall_port():
    """Add an inbound Windows Firewall rule for port 8765 (Windows only, requires UAC)."""
    if sys.platform != "win32":
        return
    try:
        # First check if a rule already exists so we don't duplicate
        check = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule",
             "name=Murmer Whisper Server"],
            capture_output=True, text=True,
            creationflags=_NO_WINDOW,
        )
        if "Murmer Whisper Server" in check.stdout:
            return  # Rule already exists

        # Rule missing — add it via an elevated PowerShell process (triggers UAC once)
        subprocess.run(
            ["powershell", "-Command",
             "Start-Process powershell "
             "-ArgumentList '-NoProfile -Command "
             'New-NetFirewallRule -DisplayName \\"Murmer Whisper Server\\" '
             "-Direction Inbound -Protocol TCP -LocalPort 8765 "
             '-Action Allow -ErrorAction SilentlyContinue\' '
             "-Verb RunAs -Wait"],
            creationflags=_NO_WINDOW,
        )
        logger.log("Firewall rule added: port 8765 open for inbound connections.")
    except Exception as e:
        logger.log(f"Firewall rule could not be added automatically: {e}", level="ERROR")


def _get_tailscale_ip() -> str | None:
    if sys.platform != "win32":
        return None
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-NetIPAddress | Where-Object {$_.IPAddress -like '100.*'} "
             "| Select-Object -First 1 -ExpandProperty IPAddress"],
            capture_output=True, text=True, timeout=5,
            creationflags=_NO_WINDOW,
        )
        ip = result.stdout.strip()
        return ip if ip else None
    except Exception:
        return None


def _get_local_ip() -> str | None:
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def _get_api_key() -> str:
    if _ENV_FILE.exists():
        for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("MURMER_API_KEY="):
                val = line.split("=", 1)[1].strip()
                if val and val != "vervang-dit-met-een-sterk-wachtwoord":
                    return val
    return ""


class ServerManagerWindow:
    def __init__(self, root: ctk.CTk, get_server_running, start_server, stop_server):
        self._root = root
        self._get_server_running = get_server_running
        self._start_server = start_server
        self._stop_server = stop_server
        self._win: ctk.CTkToplevel | None = None

    def open(self):
        if self._win and self._win.winfo_exists():
            self._win.lift()
            self._win.focus()
            return
        self._build()

    def _build(self):
        win = ctk.CTkToplevel(self._root)
        win.title("Murmer — Whisper Server")
        win.geometry("480x520")
        win.resizable(False, False)
        win.after(100, win.lift)
        self._win = win

        if sys.platform != "win32":
            if _is_installed():
                self._show_linux_installed()
            else:
                self._show_linux_not_installed()
        elif not _is_installed():
            self._show_not_installed()
        else:
            self._show_installed()

    def _show_linux_not_installed(self):
        win = self._win
        ctk.CTkLabel(win, text="Whisper Server",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(24, 4))
        ctk.CTkLabel(win, text="Turn this PC into a transcription server",
                     font=ctk.CTkFont(size=13), text_color="#888").pack(pady=(0, 16))

        scroll = ctk.CTkScrollableFrame(win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        self._linux_step(scroll, "1. Set up the server",
            "cd server\n"
            "python3 -m venv venv\n"
            "source venv/bin/activate\n"
            "pip install -r requirements.txt\n"
            "cp .env.example .env\n"
            "nano .env   # set MURMER_API_KEY"
        )
        self._linux_step(scroll, "2. Start manually",
            "python faster_whisper_server.py"
        )
        self._linux_step(scroll, "3. Or run as a systemd service",
            "sudo cp murmer-whisper.service /etc/systemd/system/\n"
            "sudo systemctl enable --now murmer-whisper"
        )

        ctk.CTkLabel(win,
                     text="Once running, configure Settings → Transcription → Mode: Remote.",
                     font=ctk.CTkFont(size=11), text_color="#666").pack(padx=24, pady=(0, 12))

    def _linux_step(self, parent, title: str, commands: str):
        ctk.CTkLabel(parent, text=title, font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#aaa").pack(anchor="w", pady=(10, 4))
        lines = commands.count("\n") + 1
        box = ctk.CTkTextbox(parent, height=lines * 20 + 16,
                             font=ctk.CTkFont(family="Consolas", size=12),
                             fg_color="#1a1a1e", corner_radius=6, wrap="none")
        box.pack(fill="x", pady=(0, 4))
        box.insert("1.0", commands)
        box.configure(state="disabled")

    def _show_linux_installed(self):
        self._clear()
        win = self._win

        running = self._get_server_running()

        ctk.CTkLabel(win, text="Whisper Server",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(24, 4))

        status_color = "#4CAF50" if running else "#888"
        status_text = "● Running" if running else "○ Stopped"
        ctk.CTkLabel(win, text=status_text, font=ctk.CTkFont(size=13),
                     text_color=status_color).pack(pady=(0, 16))

        if running:
            ctk.CTkButton(win, text="Stop Server", height=38, width=160,
                          fg_color="#8B2020", hover_color="#6B1818",
                          font=ctk.CTkFont(size=13),
                          command=self._linux_stop).pack(pady=(0, 20))
        else:
            ctk.CTkButton(win, text="Start Server", height=38, width=160,
                          font=ctk.CTkFont(size=13),
                          command=self._linux_start).pack(pady=(0, 20))

        # Connection info
        info_frame = ctk.CTkFrame(win, corner_radius=8)
        info_frame.pack(fill="x", padx=24, pady=(0, 16))

        ctk.CTkLabel(info_frame, text="Connection details",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#aaa").pack(anchor="w", padx=16, pady=(12, 6))

        local_ip = _get_local_ip()
        ip_text = local_ip if local_ip else "Not detected"
        ip_color = "#ffffff" if local_ip else "#888"
        self._info_row(info_frame, "Local IP", ip_text, ip_color)
        self._info_row(info_frame, "Port", "8765")

        api_key = _get_api_key()
        if api_key:
            masked = api_key[:6] + "•" * (len(api_key) - 6)
            key_row = ctk.CTkFrame(info_frame, fg_color="transparent")
            key_row.pack(fill="x", padx=16, pady=(2, 12))
            ctk.CTkLabel(key_row, text="API key:", font=ctk.CTkFont(size=12),
                         text_color="#666", width=90, anchor="w").pack(side="left")
            ctk.CTkLabel(key_row, text=masked, font=ctk.CTkFont(size=12),
                         text_color="#4CAF50").pack(side="left", padx=(0, 10))
            self._copy_btn = ctk.CTkButton(
                key_row, text="Copy", width=70, height=26,
                font=ctk.CTkFont(size=11),
                command=lambda k=api_key: self._copy_key(k),
            )
            self._copy_btn.pack(side="left")
        else:
            ctk.CTkLabel(info_frame,
                         text="API key not set — edit server/.env and set MURMER_API_KEY.",
                         font=ctk.CTkFont(size=11), text_color="#E07B39",
                         justify="left").pack(anchor="w", padx=16, pady=(2, 12))

        ctk.CTkLabel(win,
                     text="On your other device: Settings → Transcription → Remote\n"
                          "Enter the URL (http://IP:8765) and API key above.",
                     font=ctk.CTkFont(size=11), text_color="#666",
                     justify="left").pack(padx=24, pady=(4, 0))

    def _linux_start(self):
        self._start_server()
        self._show_linux_installed()

    def _linux_stop(self):
        self._stop_server()
        self._show_linux_installed()

    # ── Not installed ─────────────────────────────────────────────

    def _show_not_installed(self):
        self._clear()
        win = self._win

        ctk.CTkLabel(win, text="Whisper Server",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(28, 6))

        ctk.CTkLabel(win, text="Turn this PC into a transcription server",
                     font=ctk.CTkFont(size=13), text_color="#888").pack(pady=(0, 24))

        info = (
            "The Whisper Server lets other devices — like your laptop —\n"
            "use this PC's GPU for fast voice transcription.\n\n"
            "How it works:\n"
            "  1. Install the server on this PC (one time)\n"
            "  2. Make this PC reachable from your other device\n"
            "     (local network, Tailscale, or a reverse proxy)\n"
            "  3. In Murmer Settings, set Mode to Remote and\n"
            "     enter this PC's URL + the API key\n\n"
            "The server runs silently in the background and\n"
            "can be started or stopped from this menu."
        )
        ctk.CTkLabel(win, text=info, font=ctk.CTkFont(size=12),
                     text_color="#aaa", justify="left").pack(padx=32, pady=(0, 28))

        self._install_btn = ctk.CTkButton(
            win, text="Install Server", height=42,
            font=ctk.CTkFont(size=14), width=200,
            command=self._start_install,
        )
        self._install_btn.pack(pady=(0, 8))

        ctk.CTkLabel(win, text="This will download ~500 MB of dependencies.",
                     font=ctk.CTkFont(size=11), text_color="#555").pack()

    # ── Installing ────────────────────────────────────────────────

    def _start_install(self):
        self._clear()
        win = self._win

        ctk.CTkLabel(win, text="Installing Whisper Server",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(32, 8))

        self._install_status = ctk.CTkLabel(
            win, text="Creating virtual environment...",
            font=ctk.CTkFont(size=12), text_color="#aaa", wraplength=400,
        )
        self._install_status.pack(pady=(0, 16))

        self._install_bar = ctk.CTkProgressBar(win, mode="indeterminate", width=340)
        self._install_bar.pack(pady=(0, 8))
        self._install_bar.start()

        ctk.CTkLabel(win, text="This may take a few minutes. Please wait.",
                     font=ctk.CTkFont(size=11), text_color="#555").pack()

        threading.Thread(target=self._run_install, daemon=True).start()

    def _run_install(self):
        def status(msg):
            if self._win and self._win.winfo_exists():
                self._win.after(0, lambda m=msg: self._install_status.configure(text=m))

        try:
            # Create venv
            status("Creating virtual environment...")
            result = subprocess.run(
                ["python", "-m", "venv", str(_SERVER_DIR / "venv")],
                capture_output=True, text=True,
                creationflags=_NO_WINDOW,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Venv creation failed:\n{result.stderr}")

            # Install dependencies
            status("Installing dependencies (faster-whisper, FastAPI, uvicorn)...\nThis may take a few minutes.")
            result = subprocess.run(
                [str(_VENV_PYTHON), "-m", "pip", "install", "-r", str(_REQUIREMENTS), "--quiet"],
                capture_output=True, text=True,
                creationflags=_NO_WINDOW,
            )
            if result.returncode != 0:
                raise RuntimeError(f"pip install failed:\n{result.stderr}")

            # Create .env if missing
            if not _ENV_FILE.exists() and _ENV_EXAMPLE.exists():
                import shutil
                shutil.copy(_ENV_EXAMPLE, _ENV_FILE)

            # Open Windows Firewall for port 8765
            status("Configuring Windows Firewall for port 8765...")
            _open_firewall_port()

            if self._win and self._win.winfo_exists():
                self._win.after(0, self._show_installed)

        except Exception as e:
            logger.log(f"Server install failed: {e}", level="ERROR")
            if self._win and self._win.winfo_exists():
                self._win.after(0, lambda: self._show_install_error(str(e)))

    def _show_install_error(self, msg: str):
        self._clear()
        ctk.CTkLabel(self._win, text="Installation failed",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#D94040").pack(pady=(32, 12))
        ctk.CTkLabel(self._win, text=msg, font=ctk.CTkFont(size=11),
                     text_color="#aaa", wraplength=420, justify="left").pack(padx=24)
        ctk.CTkButton(self._win, text="Try again", command=self._show_not_installed,
                      width=140).pack(pady=24)

    # ── Installed ─────────────────────────────────────────────────

    def _show_installed(self):
        self._clear()
        win = self._win

        running = self._get_server_running()

        ctk.CTkLabel(win, text="Whisper Server",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(24, 4))

        status_color = "#4CAF50" if running else "#888"
        status_text = "● Running" if running else "○ Stopped"
        ctk.CTkLabel(win, text=status_text, font=ctk.CTkFont(size=13),
                     text_color=status_color).pack(pady=(0, 20))

        # Start/Stop button
        if running:
            ctk.CTkButton(win, text="Stop Server", height=38, width=160,
                          fg_color="#8B2020", hover_color="#6B1818",
                          font=ctk.CTkFont(size=13),
                          command=self._do_stop).pack(pady=(0, 24))
        else:
            ctk.CTkButton(win, text="Start Server", height=38, width=160,
                          font=ctk.CTkFont(size=13),
                          command=self._do_start).pack(pady=(0, 24))

        # Connection info
        info_frame = ctk.CTkFrame(win, corner_radius=8)
        info_frame.pack(fill="x", padx=24, pady=(0, 16))

        ctk.CTkLabel(info_frame, text="Connection details",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#aaa").pack(anchor="w", padx=16, pady=(12, 6))

        local_ip = _get_local_ip()
        tailscale_ip = _get_tailscale_ip()

        self._info_row(info_frame, "Local IP",
                       local_ip if local_ip else "Not detected",
                       "#ffffff" if local_ip else "#888")
        if tailscale_ip:
            self._info_row(info_frame, "Tailscale IP", tailscale_ip)
        self._info_row(info_frame, "Port", "8765")

        api_key = _get_api_key()
        if api_key:
            masked = api_key[:6] + "•" * (len(api_key) - 6)
            key_row = ctk.CTkFrame(info_frame, fg_color="transparent")
            key_row.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(key_row, text="API key:", font=ctk.CTkFont(size=12),
                         text_color="#666", width=90, anchor="w").pack(side="left")
            ctk.CTkLabel(key_row, text=masked, font=ctk.CTkFont(size=12),
                         text_color="#4CAF50").pack(side="left", padx=(0, 10))
            self._copy_btn = ctk.CTkButton(
                key_row, text="Copy", width=70, height=26,
                font=ctk.CTkFont(size=11),
                command=lambda k=api_key: self._copy_key(k),
            )
            self._copy_btn.pack(side="left")
        else:
            key_row = ctk.CTkFrame(info_frame, fg_color="transparent")
            key_row.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(key_row, text="API key:", font=ctk.CTkFont(size=12),
                         text_color="#666", width=90, anchor="w").pack(side="left")
            ctk.CTkLabel(key_row, text="Not set", font=ctk.CTkFont(size=12),
                         text_color="#E07B39").pack(side="left", padx=(0, 10))
            ctk.CTkButton(key_row, text="Generate", width=90, height=26,
                          font=ctk.CTkFont(size=11),
                          command=self._generate_api_key).pack(side="left")

        # Always show a local URL; add Tailscale URL if available
        display_ip = local_ip or tailscale_ip
        if display_ip:
            for label, ip in ([("Local URL", local_ip)] +
                              ([("Tailscale URL", tailscale_ip)] if tailscale_ip else [])):
                if not ip:
                    continue
                url = f"http://{ip}:8765"
                url_row = ctk.CTkFrame(info_frame, fg_color="transparent")
                url_row.pack(fill="x", padx=16, pady=(2, 4))
                ctk.CTkLabel(url_row, text=f"{label}:", font=ctk.CTkFont(size=12),
                             text_color="#666", width=90, anchor="w").pack(side="left")
                ctk.CTkLabel(url_row, text=url,
                             font=ctk.CTkFont(family="Consolas", size=11),
                             text_color="#4a9eff").pack(side="left", padx=(0, 10))
                btn = ctk.CTkButton(url_row, text="Copy", width=70, height=26,
                                    font=ctk.CTkFont(size=11),
                                    command=lambda u=url: self._copy_url(u))
                btn.pack(side="left")
            # Add bottom padding
            ctk.CTkFrame(info_frame, fg_color="transparent", height=8).pack()
        else:
            ctk.CTkLabel(info_frame,
                         text="No IP detected. Connect via a reverse proxy\n"
                              "and enter the URL manually in Settings → Transcription.",
                         font=ctk.CTkFont(size=11), text_color="#888", justify="left").pack(
                anchor="w", padx=16, pady=(4, 12))

        # Autostart toggle
        autostart_row = ctk.CTkFrame(win, fg_color="transparent")
        autostart_row.pack(fill="x", padx=24, pady=(12, 4))
        ctk.CTkLabel(autostart_row, text="Start server when Murmer launches",
                     font=ctk.CTkFont(size=12)).pack(side="left")
        self._autostart_var = ctk.BooleanVar(value=config.WHISPER_SERVER_AUTOSTART)
        ctk.CTkSwitch(autostart_row, text="", variable=self._autostart_var,
                      width=52, command=self._save_autostart).pack(side="right")

        ctk.CTkLabel(win,
                     text="On your other device: open Murmer → Settings → Transcription\n"
                          "Set Mode to Remote and enter the URL and API key above.",
                     font=ctk.CTkFont(size=11), text_color="#666",
                     justify="left").pack(padx=24, pady=(4, 0))

    def _info_row(self, parent, label: str, value: str, value_color: str = "#ffffff"):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=2)
        ctk.CTkLabel(row, text=f"{label}:", font=ctk.CTkFont(size=12),
                     text_color="#666", width=90, anchor="w").pack(side="left")
        ctk.CTkLabel(row, text=value, font=ctk.CTkFont(size=12),
                     text_color=value_color, anchor="w").pack(side="left")

    def _save_autostart(self):
        config.save({"WHISPER_SERVER_AUTOSTART": self._autostart_var.get()})
        state = "ingeschakeld" if self._autostart_var.get() else "uitgeschakeld"
        logger.log(f"Whisper Server autostart {state}.")

    def _copy_url(self, url: str):
        self._win.clipboard_clear()
        self._win.clipboard_append(url)
        self._url_copy_btn.configure(text="Copied!", fg_color="#2d6e2d")
        self._win.after(2000, lambda: self._url_copy_btn.configure(text="Copy", fg_color=("#3B8ED0", "#1F6AA5")))

    def _copy_key(self, key: str):
        self._win.clipboard_clear()
        self._win.clipboard_append(key)
        self._copy_btn.configure(text="Copied!", fg_color="#2d6e2d")
        self._win.after(2000, lambda: self._copy_btn.configure(text="Copy", fg_color=("#3B8ED0", "#1F6AA5")))

    def _generate_api_key(self):
        import secrets
        key = secrets.token_hex(32)
        try:
            if _ENV_FILE.exists():
                lines = _ENV_FILE.read_text(encoding="utf-8").splitlines()
                new_lines = []
                replaced = False
                for line in lines:
                    if line.startswith("MURMER_API_KEY="):
                        new_lines.append(f"MURMER_API_KEY={key}")
                        replaced = True
                    else:
                        new_lines.append(line)
                if not replaced:
                    new_lines.append(f"MURMER_API_KEY={key}")
                _ENV_FILE.write_text("\n".join(new_lines), encoding="utf-8")
            else:
                _ENV_FILE.write_text(f"MURMER_API_KEY={key}\n", encoding="utf-8")
            logger.log("Whisper Server API key gegenereerd en opgeslagen.")
            # Herstart server zodat nieuwe key actief wordt
            if self._get_server_running():
                self._stop_server()
                self._start_server()
                logger.log("Whisper Server herstart met nieuwe API key.")
        except Exception as e:
            logger.log(f"API key opslaan mislukt: {e}", level="ERROR")
        self._show_installed()

    def _do_start(self):
        self._start_server()
        self._show_installed()

    def _do_stop(self):
        self._stop_server()
        self._show_installed()

    # ── Helpers ───────────────────────────────────────────────────

    def _clear(self):
        if not self._win:
            return
        for widget in self._win.winfo_children():
            widget.destroy()
