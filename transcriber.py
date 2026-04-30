import numpy as np
from faster_whisper import WhisperModel
import config


class Transcriber:
    def __init__(self):
        self.model: WhisperModel | None = None

    def load(self):
        print(f"Loading Whisper {config.WHISPER_MODEL} on {config.WHISPER_DEVICE} ({config.WHISPER_COMPUTE_TYPE})...")
        self.model = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
        )
        print("Whisper model ready.")

    def transcribe(self, audio: np.ndarray) -> tuple[str, str]:
        segments, info = self.model.transcribe(
            audio,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text, info.language
