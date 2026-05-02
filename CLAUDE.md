# Murmer

A local voice dictation app - free alternative to Murmur (€15/month).

## What it does
- Hold a configurable hotkey anywhere on Windows -> records microphone
- Release -> transcribes with OpenAI Whisper (local or remote server)
- Optionally cleans up the text with Claude Haiku (removes filler words, fixes punctuation)
- Pastes result into whatever app is focused
- System tray app with waveform icon (grey = idle, red = recording, amber = processing)

## Stack
- **faster-whisper** - local Whisper transcription (large-v3 on CUDA, medium on CPU)
- **Claude Haiku** - optional AI text cleanup via Anthropic API (`claude-haiku-4-5-20251001`)
- **customtkinter** - settings panel (sidebar layout), splash screen, log window, server manager UI
- **pystray** - system tray icon with dynamic waveform bars (runs detached in background thread)
- **keyboard** - global push-to-talk hotkey
- **sounddevice** - microphone recording with device enumeration
- **FastAPI + uvicorn** - remote transcription server (server/)
- Settings persisted to `settings.json`; secrets in `.env`

## File overview
| File | Purpose |
|---|---|
| `main.py` | Entry point, orchestration, tray icon, single-instance check, restart, server management |
| `config.py` | Load/save settings from `settings.json` + `.env` |
| `recorder.py` | Microphone capture via sounddevice; device listing with deduplication |
| `transcriber.py` | faster-whisper transcription (local) or HTTP POST to remote server |
| `cleaner.py` | Claude Haiku cleanup; style profiles + user profile injected into system prompt |
| `paster.py` | Clipboard swap + Ctrl+V into active window |
| `overlay.py` | Borderless recording indicator (bottom-right, pulsing dot + timer) |
| `settings_window.py` | Sidebar settings UI (720x500, resizable); 6 sections: General, Audio, Transcription, AI Cleanup, Display, Profile |
| `splash.py` | Loading screen shown while Whisper model loads |
| `autostart.py` | Windows registry auto-start helper |
| `logger.py` | Central logging: in-memory buffer + RESULT-level history file in %LOCALAPPDATA%\Murmer\ |
| `log_window.py` | Activity log window: compact (RESULT/ERROR only) and debug (all) modes |
| `server_manager_window.py` | Whisper Server manager: install, start/stop, API key gen, Tailscale connection info, firewall rule |
| `create_icon.py` | Generates murmer.ico with amber waveform bars (run once, output committed) |
| `murmer.iss` | Inno Setup 6 installer script |
| `build_installer.bat` | One-click installer build |
| `server/faster_whisper_server.py` | FastAPI transcription server, X-API-Key auth, /transcribe + /health |
| `server/requirements.txt` | faster-whisper, fastapi, uvicorn[standard], python-dotenv, python-multipart |
| `server/.env.example` | Template: MURMER_API_KEY, WHISPER_MODEL, WHISPER_DEVICE, etc. |
| `server/murmer-whisper.service` | systemd unit for Lumen (Ubuntu); sets LD_LIBRARY_PATH for CUDA |
| `server/setup_windows.bat` | Creates server venv + installs dependencies (Windows) |
| `server/start_server.bat` | Starts the server in background (Windows) |
| `server/stop_server.bat` | Kills the server process (Windows) |

## Current state (fully working as of last session)
- **v1.0 released on GitHub** (private repo, release published with installer)
- App works on main PC (RTX 4070, CUDA, large-v3) and laptop (CPU, medium, remote mode)
- Installer (`dist/Murmer-Setup-v1.0.exe`) works end-to-end on clean Windows 11
- **Early startup window** - minimal tkinter window appears instantly on launch
- **Splash screen** - customtkinter loading screen with indeterminate progress bar
- **Single-instance check** - Windows named mutex prevents duplicate launches
- **Hotkey capture** - "Capture key" button; hotkey rehooks live after save without restart
- **Restart button** - in tray menu and as "Save & Restart" in settings
- **Language detection** - Whisper detects language, passes it to Haiku to prevent translation
- **AI cleanup prompt** - input wrapped in `<transcription>` tags
- **CPU fallback** - installer auto-writes medium/cpu/int8 settings if no CUDA detected
- **Audio device selection** - dropdown with deduplication (MME/DS/WASAPI same device shown once)
- **Waveform tray icon** - dark rounded square, 7 bars, grey/red/amber; murmer.ico for shortcuts
- **Activity log** - compact/debug modes, Clear button, Open history button
- **History file** - RESULT entries written to `%LOCALAPPDATA%\Murmer\history.log`
- **Transcription mode** - Local or Remote toggle in Settings -> Transcription
- **Remote transcription** - POSTs WAV to server with X-API-Key header; skips local model load
- **Style profiles** - none/formal/informal/technical/custom; injected into Haiku system prompt
- **Word corrections** - dict stored in settings.json; applied post-transcription with \b word boundaries; correct spellings fed to Whisper as initial_prompt for local mode
- **User profile** - free text injected as context into Haiku system prompt
- **Saved servers** - list of {name, url, api_key} in settings.json; dropdown in Transcription section fills URL+key on select; Save current as... / Delete buttons; saves immediately to config
- **Settings UI redesign** - sidebar navigation (720x500, resizable); sections: General, Audio, Transcription, AI Cleanup, Display, Profile; CTkScrollableFrame per section
- **Windows Whisper Server management** - install (venv + pip in background thread), start/stop, API key gen/copy, Tailscale IP detection, Remote URL copy, autostart toggle, dynamic tray menu status
- **Server status persistence** - `_server_running()` checks subprocess poll AND socket port 8765
- **Orphan process cleanup** - PowerShell WMI kills all faster_whisper_server processes on stop
- **Firewall rule** - `_open_firewall_port()` adds inbound rule for port 8765 via UAC-elevated PowerShell during server install; skips if rule already exists
- **README** on GitHub with full setup instructions, dependency links, remote server guide
- Git repo: https://github.com/R3PC0N/murmer (private, v1.0 release published)

## Remote transcription servers

### Lumen (Ubuntu 24.04, GTX 1650)
- Deployed at `/home/r3pc0n/murmer-server/`, runs as systemd service `murmer-whisper`
- CUDA libraries: `/usr/local/lib/ollama/cuda_v12/` (set via `LD_LIBRARY_PATH` in service file)
- Tailscale IP: `100.86.210.76`, port `8765`
- API key in `/home/r3pc0n/murmer-server/.env` as `MURMER_API_KEY`

### Windows main PC (RTX 4070)
- Managed via Murmer tray -> "Whisper Server..."
- Server installed to `server/venv/`
- API key stored in `server/.env` as `MURMER_API_KEY`
- Tailscale IP shown in Server Manager window
- Mullvad VPN conflicts with Tailscale - add tailscale.exe to Mullvad split tunnel exclusions

## Config defaults
- Hotkey: `f9`
- Audio device: `null` (system default)
- Model: `large-v3` (CUDA) / `medium` (CPU, set by installer if no CUDA)
- Whisper device: `cuda` / compute type: `float16`
- Transcription mode: `local`
- Remote URL: `""` / Remote API key: `""`
- Whisper Server autostart: `false`
- Saved servers: `[]`
- AI cleanup: enabled (requires `ANTHROPIC_API_KEY` in `.env`)
- Transcription style: `none`
- Custom style prompt: `""`
- User profile: `""`
- Word corrections: `{}`
- Overlay: enabled
- Auto-start: disabled

## Next planned feature
**Linux variant** - native Linux client (no Windows dependencies like winsound, pystray tray, keyboard library). Key differences to handle:
- `winsound.Beep` -> needs replacement (e.g. `subprocess` + `paplay`/`aplay`, or silent)
- `pystray` - works on Linux with AppIndicator/GTK, but needs testing
- `keyboard` library - works on Linux but requires root or `input` group membership
- `paster.py` - `xdotool` or `xclip` + `xdotool key ctrl+v` instead of Windows clipboard API
- `ctypes.windll` (single instance mutex) - needs Linux equivalent (lock file)
- `winsound` import at top of main.py will fail on Linux
- Installer: replace Inno Setup with .deb package or AppImage
- Consider a single codebase with platform detection vs separate entry points

## Known issues / next steps
1. **Model download progress** - on first launch, no % indicator during download
2. **Version bump workflow** - no process yet for bumping AppVersion in murmer.iss
3. **Linux variant** - next major feature (see above)
4. **Landing page / public release** - plan to build a website before making repo public and posting to Reddit (r/selfhosted etc.)

## Development workflow
```bat
# Run locally
cd D:\Code-Projects\wispr-app
venv\Scripts\activate
python main.py

# Build installer (requires Inno Setup 6)
# Open murmer.iss in Inno Setup -> F9
# Output: dist\Murmer-Setup-v1.0.exe

# Commit and push
git add .
git commit -m "description"
git push
```
