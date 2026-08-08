# Murmur Agent Guidance

## Project identity

Murmur is an existing cross-platform Python desktop application for push-to-talk dictation and transcription. It supports Windows and Linux; treat native Wayland as an additional supported Linux target, not as a replacement for Windows or X11. Extend the current application rather than treating it as a new or Linux-only project.

## Architecture

- `main.py` is the application entrypoint and coordinates startup, recording, transcription, cleanup, text insertion, global hotkeys, tray state, windows, and the optional local server.
- The settings, activity log, server manager, and splash are pywebview windows backed by HTML in `ui/`; their Python controllers are `settings_window.py`, `log_window.py`, `server_manager_window.py`, and `splash.py`.
- `pystray` provides the tray. Linux initialization currently integrates it with GTK/AppIndicator from `main.py`.
- `overlay.py` implements the recording overlay with Tkinter.
- `recorder.py` records through `sounddevice`/PortAudio and enumerates input devices.
- `transcriber.py` uses faster-whisper locally or sends WAV audio to a configured remote HTTP server. `cleaner.py` optionally cleans transcription text with Anthropic.
- `server/faster_whisper_server.py` is the FastAPI transcription server; server dependencies and service examples live under `server/`.
- `config.py` loads defaults, `.env`, and `settings.json`. On Linux, `app_paths.py` places mutable client configuration and state under XDG locations and imports legacy source-relative files without deleting them. Windows paths remain unchanged.
- `paster.py` selects Windows, Linux/X11, or Linux/Wayland text insertion. Windows uses clipboard plus simulated paste, X11 uses `xdotool`, and the tested Wayland backend uses `wtype`.
- `hotkeys.py` selects the global-hotkey backend. Windows uses `keyboard`, Linux/X11 uses `pynput`, and Hyprland/native Wayland uses temporary compositor runtime bindings through `hyprctl`. Other native-Wayland compositors receive a clear unsupported-backend error rather than an X11 fallback.
- `autostart.py` uses the Windows registry or an XDG autostart desktop file. The portable Linux bootstrap installs the visible XDG application entry and icon.
- Platform-specific code exists in several modules. Keep new platform decisions explicit and narrowly scoped rather than spreading ad hoc `sys.platform` checks.

## Platform support philosophy

- Preserve working Windows and Linux/X11 behavior while adding native Wayland support.
- Isolate platform-sensitive operations behind small functions or backends when that improves testability without forcing a broad refactor.
- Prefer capability and session detection over distribution detection. Use distro-specific logic only for genuinely distro-specific package names or installation instructions.
- Prefer portable Linux and XDG conventions over desktop-specific or distro-specific hacks.
- Compositor-specific integration is acceptable when necessary, but should not become the generic Linux implementation without a technical reason.
- A Wayland session commonly exports both `WAYLAND_DISPLAY` and `DISPLAY` because XWayland is available. Do not infer that the session is X11 merely from `DISPLAY`; native Wayland must win when appropriate.

## Repository boundaries

Murmur source and application development belong in this repository. Machine provisioning does not.

`~/workstation` is a separate repository that reproducibly provisions this particular Omarchy workstation. Do not modify it during Murmur work unless the user explicitly requests a workstation change. Do not copy Murmur source, virtual environments, downloaded models, credentials, or mutable application state into it.

Use this distinction:

- Murmur: “What does the application require?”
- Workstation: “How does this machine provide those requirements?”

Report workstation-level dependencies clearly so they can be recorded separately when requested.

## Linux desktop compatibility

- Distinguish native Wayland, XWayland applications, and an actual X11 session.
- Wayland text insertion in `paster.py` uses the live-tested `wtype` backend. It sends literal text through stdin with a small inter-key delay and normalizes tabs to spaces. Preserve its shell-safety and error reporting.
- X11 retains the `xdotool` backend. Do not remove it when changing Wayland behavior.
- Clipboard access and keyboard/input injection are separate capabilities. Writing the clipboard does not by itself paste into the focused application.
- Hyprland global hotkeys use temporary runtime bindings and conflict detection from `hotkeys.py`; Murmur does not permanently edit compositor configuration. Do not grant broad input-device access, add users to input-related groups, or add udev rules unless another implemented backend demonstrably requires it and the security tradeoff is documented.
- PipeWire is the expected modern Linux audio environment, commonly reached through PortAudio compatibility. Keep audio handling portable where practical and test actual device enumeration and recording in a live session.

## Filesystem and state policy

Linux client settings, AI-cleanup configuration, history, diagnostics, locks, sockets, and temporary runtime artifacts use the appropriate XDG configuration, data, state, and runtime locations through `app_paths.py`. Legacy source-relative client configuration and the former `~/.local/share/Murmur` logs are imported without deletion when the XDG destination is absent. Keep application source separate from mutable user state, preserve migration compatibility, and do not bypass the central path helper.

The optional server still manages its own credentials under `server/`; do not silently treat server deployment state as client XDG state. Windows paths and behavior remain unchanged.

## Dependencies

- Consider Python compatibility explicitly. Do not assume the newest Arch system Python is automatically supported by Murmur or all of its dependencies.
- Check compatibility of native or wheel-backed dependencies such as faster-whisper/CTranslate2, NumPy, pywebview/GTK/WebKitGTK, `sounddevice`, and PortAudio.
- Capability-check external executables before invoking them, use subprocess argument arrays or stdin instead of shell-built commands, and report failures clearly.
- Application code must not silently install system packages. Keep package installation in explicit setup or packaging workflows.

## Testing expectations

- Add focused tests for platform/session selection and backend command construction where practical.
- Run appropriate syntax checks for every modified Python or shell file.
- Run `git diff --check`, inspect the final diff, and inspect `git status` before completion.
- Manually test desktop integration that cannot be validated headlessly. Depending on the feature, Wayland testing may include native Wayland and XWayland applications, terminals, browsers/Electron, Unicode, multiple monitors, focus behavior, and compositor interaction.
- Do not knowingly regress Windows behavior while implementing Linux support, or X11 behavior while implementing Wayland support. State when a platform could not be exercised locally.

## Git and workflow

- Inspect relevant code, documentation, repository instructions, and working-tree state before changing files.
- Keep compatibility fixes narrow and reviewable. Avoid broad architecture changes while addressing a specific platform blocker.
- Preserve unrelated user changes.
- Do not stage, commit, push, change repository visibility, or perform unrelated GitHub operations unless explicitly requested.
- A request to commit does not authorize pushing. Never push automatically unless the user also explicitly requests it.

## Documentation discipline

Clearly distinguish confirmed repository facts, observations from the current live environment, and hypotheses that still require manual testing. Do not turn temporary implementation plans, local package state, current commits, or phase-specific milestones into permanent architecture documentation.
