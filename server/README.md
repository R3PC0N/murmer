# Murmur Whisper Server

Optional FastAPI service that exposes faster-whisper transcription over HTTP. The desktop client can use it instead of loading a local model.

## Setup

The included `murmur-whisper.service` is a template. Before installing it, change its `User`, `WorkingDirectory`, `EnvironmentFile`, and `ExecStart` values to match the server account and installation path.

```bash
sudo mkdir -p /opt/murmur-server
sudo cp faster_whisper_server.py requirements.txt .env.example /opt/murmur-server/
sudo chown -R YOUR_USER:YOUR_USER /opt/murmur-server

cd /opt/murmur-server
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
# Edit .env before starting the server.

sudo cp murmur-whisper.service /etc/systemd/system/
# Edit /etc/systemd/system/murmur-whisper.service for your user and paths.
sudo systemctl daemon-reload
sudo systemctl enable --now murmur-whisper
```

## Configuration

```env
MURMUR_API_KEY=choose-a-strong-secret
WHISPER_MODEL=medium
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
HOST=0.0.0.0
PORT=8765
```

The server constructs the configured model directly. Unlike the desktop client's built-in default runtime, it does not automatically fall back from CUDA to CPU. For CPU operation, configure a supported combination explicitly, for example:

```env
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

## Authentication and network safety

Set `MURMUR_API_KEY` to enable authentication. Clients must send the same value in the `X-API-Key` header.

The current server permits unauthenticated requests when `MURMUR_API_KEY` is empty and listens on all interfaces by default (`HOST=0.0.0.0`). Do not expose that configuration to an untrusted network. Use a strong API key and protect remote traffic with HTTPS or a trusted VPN; the API key alone does not encrypt audio in transit.

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/transcribe` | Accept WAV audio and return text plus Whisper's language |
| GET | `/health` | Return basic model/device status |

### Transcription language

`POST /transcribe` accepts an optional multipart `language` field:

| Value | Behavior |
|---|---|
| omitted or empty | Automatic Whisper language detection |
| `nl` | Force Dutch |
| `en` | Force English |

Explicit language selection from the desktop client requires a server version that supports this field. Older servers continue using automatic detection.

```bash
curl http://localhost:8765/health

# Automatic language detection
curl -X POST http://localhost:8765/transcribe \
  -H "X-API-Key: YOUR_KEY" \
  -F "audio=@test.wav" \
  -F "language="

# Forced Dutch
curl -X POST http://localhost:8765/transcribe \
  -H "X-API-Key: YOUR_KEY" \
  -F "audio=@test.wav" \
  -F "language=nl"
```

## Service management

```bash
sudo systemctl status murmur-whisper
sudo systemctl restart murmur-whisper
sudo journalctl -u murmur-whisper -f
```
