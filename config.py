import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_SETTINGS_FILE = Path(__file__).parent / "settings.json"

_DEFAULTS: dict = {
    "PUSH_TO_TALK_KEY": "f9",
    "AUDIO_DEVICE": None,
    "WHISPER_MODEL": "large-v3",
    "WHISPER_DEVICE": "cuda",
    "WHISPER_COMPUTE_TYPE": "float16",
    "WHISPER_SERVER_AUTOSTART": False,
    "TRANSCRIPTION_MODE": "local",
    "REMOTE_WHISPER_URL": "",
    "REMOTE_WHISPER_API_KEY": "",
    "AI_CLEANUP_ENABLED": True,
    "ANTHROPIC_API_KEY": "",
    "SHOW_OVERLAY": True,
    "AUTO_START": False,
}

# Non-configurable constants
SAMPLE_RATE = 16000
MIN_RECORDING_SAMPLES = 4800
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"


def _load() -> dict:
    data = dict(_DEFAULTS)
    if _SETTINGS_FILE.exists():
        with open(_SETTINGS_FILE) as f:
            data.update(json.load(f))
    env_key = os.getenv("ANTHROPIC_API_KEY")
    if env_key:
        data["ANTHROPIC_API_KEY"] = env_key
    return data


def save(updates: dict):
    current = _load()
    current.update(updates)
    # Don't persist the API key to disk if it came from .env
    if os.getenv("ANTHROPIC_API_KEY"):
        current.pop("ANTHROPIC_API_KEY", None)
    with open(_SETTINGS_FILE, "w") as f:
        json.dump(current, f, indent=2)
    _apply(current)


def _apply(data: dict):
    g = globals()
    for k, v in data.items():
        g[k] = v


_apply(_load())
