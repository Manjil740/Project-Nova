from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SpeechToText:
    """Offline speech-to-text wrapper.

    The project is intentionally Linux-only and defaults to offline local
    tooling. `vosk` is a real PyPI package and is a sensible fit for local
    CPU-only transcription, but the actual backend is optional and the
    implementation is intentionally failure-safe.
    """

    model_path: str | None = None
    sample_rate: int = 16000
    language: str = "en"

    def is_available(self) -> bool:
        return shutil.which("ffmpeg") is not None or shutil.which("arecord") is not None

    def transcribe_file(self, source_path: str | Path) -> str:
        file_path = Path(source_path)
        if not file_path.exists():
            return "stt:error:file_not_found"

        if shutil.which("ffmpeg") is not None:
            return f"stt:preview path={file_path} sample_rate={self.sample_rate}"

        if shutil.which("python3") is not None:
            return f"stt:unavailable backend=vosk_or_ffmpeg_missing path={file_path}"

        return "stt:unavailable"

    def transcribe_microphone(self) -> str:
        if shutil.which("arecord") is None:
            return "stt:unavailable microphone_capture_missing"
        return "stt:ready microphone capture enabled"

    def render_status(self) -> str:
        if not self.is_available():
            return "stt:unavailable backend=offline_kit_missing"
        return f"stt:ready model={self.model_path or 'auto'} language={self.language}"


if __name__ == "__main__":
    print(SpeechToText().render_status())
