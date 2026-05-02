# Murmer

**Free, local voice dictation for Windows - a Murmur alternative.**

Hold a key, speak, release. Murmer transcribes your voice using [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and pastes the result into whatever app you have focused. Optionally, Claude Haiku cleans up filler words and fixes punctuation before pasting.

No subscription. No cloud. Your audio never leaves your machine - unless you choose to use a remote server you control yourself.

---

## Features

- **Push-to-talk** - hold any configurable key to record, release to transcribe and paste
- **Local transcription** - runs Whisper entirely on your own GPU or CPU, no internet required
- **Remote transcription** - offload transcription to another PC (e.g. a desktop with a powerful GPU) over [Tailscale](https://tailscale.com)
- **AI cleanup** - Claude Haiku removes filler words, fixes punctuation and capitalization, and preserves your language (Dutch, English, or mixed)
- **Style profiles** - choose Formal, Informal, Technical, or write your own style instruction
- **User profile** - tell Haiku who you are so it can apply context to every transcription
- **Word corrections** - force correct spelling for names, terms or brand names Whisper gets wrong; applied even without AI cleanup
- **Saved servers** - store multiple remote server configurations and switch between them instantly
- **Audio device selection** - choose any input device from settings
- **Activity log** - compact or debug view of every transcription session; full history saved to disk
- **Windows Whisper Server manager** - install, start, stop and configure a local Whisper server directly from the tray icon
- **System tray** - runs silently in the background, waveform icon changes colour for idle / recording / processing
- **Single installer** - one `.exe` sets up a Python virtual environment and all dependencies automatically

---

## Requirements

### Always required

| Dependency | Version | Download |
|---|---|---|
| **Windows** | 10 or 11 (64-bit) | - |
| **Python** | 3.10 or newer | [python.org/downloads](https://www.python.org/downloads/) |

> ⚠ During Python installation, tick **"Add Python to PATH"**.

### For GPU transcription (recommended)

| Dependency | Version | Download |
|---|---|---|
| **NVIDIA GPU Driver** | Latest | [nvidia.com/drivers](https://www.nvidia.com/Download/index.aspx) |
| **NVIDIA CUDA Toolkit** | 12.x | [developer.nvidia.com/cuda-toolkit-archive](https://developer.nvidia.com/cuda-toolkit-archive) |

Without CUDA, Murmer falls back to CPU transcription automatically. The installer detects this and sets a lighter model (`medium`, `int8`) as the default.

### For AI cleanup (optional)

| Dependency | Notes | Link |
|---|---|---|
| **Anthropic API key** | Free tier available | [console.anthropic.com](https://console.anthropic.com) |

### For remote transcription (optional)

| Dependency | Notes | Download |
|---|---|---|
| **Tailscale** | Install on both devices | [tailscale.com/download](https://tailscale.com/download) |

---

## Installation

1. Download the latest installer from [Releases](https://github.com/R3PC0N/murmer/releases)
2. Run `Murmer-Setup-vX.X.exe`
3. The installer will:
   - Create a Python virtual environment
   - Install all Python dependencies
   - Create a Start Menu shortcut (and optionally a desktop shortcut)
4. On first launch, Murmer downloads the Whisper speech model (~300 MB for `medium`, ~1.5 GB for `large-v3`). A loading screen will appear - just wait until it disappears.

---

## First-run setup

### 1. AI cleanup (optional but recommended)

Open `%LOCALAPPDATA%\Murmer\.env` in a text editor and add your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Or enter it directly in **Settings → AI Cleanup**.

### 2. Start dictating

Murmer starts in the system tray. Hold **F9** anywhere, speak, release. The transcribed text is pasted into your active window.

The hotkey can be changed in **Settings → General**.

---

## Settings overview

Open Settings from the tray icon (right-click → Settings).

| Section | What you can configure |
|---|---|
| **General** | Push-to-talk key, start with Windows |
| **Audio** | Input device |
| **Transcription** | Local or remote mode, Whisper model and device, saved remote servers |
| **AI Cleanup** | Enable/disable Claude Haiku, Anthropic API key |
| **Display** | Recording overlay |
| **Profile** | Transcription style, user context, word corrections |

### Word corrections

In **Profile → Word corrections**, add one correction per line:

```
murmer=Murmer
tailscale=Tailscale
cuda=CUDA
```

Corrections are applied after transcription using whole-word matching. They work even when AI cleanup is disabled.

### Style profiles

Choose a style in **Profile → Transcription style**:

| Style | Effect |
|---|---|
| `none` | No style instruction - only filler removal and punctuation fixes |
| `formal` | Complete sentences, professional tone |
| `informal` | Casual tone, contractions allowed |
| `technical` | Technical terms and acronyms preserved exactly |
| `custom` | Write your own instruction |

---

## Remote transcription

Murmer can send audio to a Whisper server running on another machine - useful if your laptop is slow but you have a powerful desktop or home server.

### How it works

1. The server runs a FastAPI service that accepts audio and returns transcribed text
2. Communication is secured with an API key
3. Devices connect to each other over [Tailscale](https://tailscale.com), a zero-config VPN

### Setting up Tailscale

1. Install Tailscale on both devices: [tailscale.com/download](https://tailscale.com/download)
2. Sign in with the same account on both
3. Both devices will appear in your Tailscale admin panel at [login.tailscale.com/admin/machines](https://login.tailscale.com/admin/machines)
4. Note the `100.x.x.x` IP address of the server machine

> ⚠ If you use a VPN (e.g. Mullvad) on the server machine, add Tailscale to its split-tunnel exclusions so both can run simultaneously.

### Windows server (via Murmer UI)

If your server is another Windows PC with Murmer installed:

1. On the server PC: right-click the Murmer tray icon → **Whisper Server...**
2. Click **Install Server** (one-time setup, downloads ~500 MB)
3. Click **Generate** to create an API key
4. Note the **Remote URL** and **API key** shown in the window
5. On the client PC: open **Settings → Transcription**, switch to **Remote**, paste the URL and key
6. Click **Save current as...** to save this server for quick access later

The server can be started and stopped from the tray icon at any time. Enable **"Start server when Murmer launches"** to have it start automatically.

### Linux server (Ubuntu / Debian)

Requirements: Python 3.10+, CUDA 12.x (for GPU), or CPU-only.

```bash
# Clone and enter the server directory
git clone https://github.com/R3PC0N/murmer.git
cd murmer/server

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env  # Set MURMER_API_KEY and optionally WHISPER_MODEL, WHISPER_DEVICE
```

**.env example:**
```
MURMER_API_KEY=your-strong-random-key
WHISPER_MODEL=medium
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
```

**Run manually:**
```bash
python faster_whisper_server.py
```

**Run as a systemd service:**
```bash
sudo cp murmer-whisper.service /etc/systemd/system/
# Edit the service file to match your paths and username
sudo systemctl enable --now murmer-whisper
```

> If your CUDA libraries are in a non-standard location (e.g. installed via Ollama), add the path to `LD_LIBRARY_PATH` in the service file:
> ```
> Environment="LD_LIBRARY_PATH=/usr/local/lib/ollama/cuda_v12"
> ```

**Verify the server is running:**
```bash
curl http://localhost:8765/health
# {"status":"ok","model":"medium","device":"cuda"}
```

---

## Activity log

Right-click the tray icon → **Activity log** to see recent transcriptions.

- **Compact** - shows transcription results and errors only
- **Debug** - shows every step including raw Whisper output before cleanup

Full history is saved to `%LOCALAPPDATA%\Murmer\history.log`. Open it via tray → **Open history**.

---

## Building from source

```bat
git clone https://github.com/R3PC0N/murmer.git
cd murmer

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

python main.py
```

**Building the installer** (requires [Inno Setup 6](https://jrsoftware.org/isdl.php)):

```
Open murmer.iss in Inno Setup → press F9
Output: dist\Murmer-Setup-vX.X.exe
```

---

## Privacy

- Audio is processed locally by default and never sent anywhere
- When using remote mode, audio is sent over an encrypted Tailscale connection to a server you control
- AI cleanup sends transcribed text (not audio) to the Anthropic API if enabled

---

## License

MIT - see [LICENSE](LICENSE)
