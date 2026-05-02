# Murmer Whisper Server

FastAPI service that exposes faster-whisper transcription over HTTP.
Runs on Lumen (Ubuntu 24.04) as a systemd service.

## Setup

```bash
# 1. Maak de server map aan en kopieer bestanden
sudo mkdir -p /opt/murmer-server
sudo cp faster_whisper_server.py requirements.txt /opt/murmer-server/
sudo chown -R r3pc0n:r3pc0n /opt/murmer-server

# 2. Maak virtualenv en installeer dependencies
cd /opt/murmer-server
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# 3. Maak .env aan
cp .env.example .env
nano .env   # Vul MURMER_API_KEY in

# 4. Installeer en start de systemd service
sudo cp murmer-whisper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable murmer-whisper
sudo systemctl start murmer-whisper

# 5. Controleer status
sudo systemctl status murmer-whisper
```

## .env configuratie

```env
MURMER_API_KEY=kies-een-sterk-wachtwoord
WHISPER_MODEL=medium
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
HOST=0.0.0.0
PORT=8765
```

## Endpoint

| Method | Path | Omschrijving |
|--------|------|--------------|
| POST | `/transcribe` | Stuur WAV audio, ontvang tekst terug |
| GET | `/health` | Controleer of de service draait |

**Headers:** `X-API-Key: <jouw key>`

## Testen

```bash
curl -X GET http://<tailscale-ip>:8765/health

curl -X POST http://<tailscale-ip>:8765/transcribe \
  -H "X-API-Key: jouw-key" \
  -F "audio=@test.wav"
```

## Service beheren

```bash
sudo systemctl status murmer-whisper
sudo systemctl restart murmer-whisper
sudo journalctl -u murmer-whisper -f   # live logs bekijken
```
