import io
import wave

import numpy as np
import requests
from faster_whisper import WhisperModel

import config
import logger


def _to_wav_bytes(audio: np.ndarray) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(config.SAMPLE_RATE)
        wf.writeframes((audio * 32767).astype(np.int16).tobytes())
    return buf.getvalue()


class Transcriber:
    def __init__(self):
        self.model: WhisperModel | None = None

    def load(self):
        if config.TRANSCRIPTION_MODE == "remote":
            logger.log(f"Transcription mode: remote ({config.REMOTE_WHISPER_URL})")
            return
        logger.log(f"Loading Whisper {config.WHISPER_MODEL} on {config.WHISPER_DEVICE} ({config.WHISPER_COMPUTE_TYPE})...")
        self.model = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
        )
        logger.log("Whisper model ready.")

    def transcribe(self, audio: np.ndarray) -> tuple[str, str]:
        if config.TRANSCRIPTION_MODE == "remote":
            return self._transcribe_remote(audio)
        return self._transcribe_local(audio)

    def _transcribe_local(self, audio: np.ndarray) -> tuple[str, str]:
        segments, info = self.model.transcribe(
            audio,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text, info.language

    def _transcribe_remote(self, audio: np.ndarray) -> tuple[str, str]:
        url = config.REMOTE_WHISPER_URL.rstrip("/") + "/transcribe"
        headers = {"X-API-Key": config.REMOTE_WHISPER_API_KEY}
        wav = _to_wav_bytes(audio)
        resp = requests.post(
            url,
            headers=headers,
            files={"audio": ("audio.wav", wav, "audio/wav")},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["text"], data["language"]
