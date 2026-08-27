from __future__ import annotations

import shlex
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(slots=True)
class TTSEngine:
    """Local offline text-to-speech wrapper.

    Prefer the system `espeak-ng` binary when present because it is a real,
    lightweight Linux package and does not require a cloud API.
    """

    voice: str = "en-us"
    rate: int = 175

    def is_available(self) -> bool:
        return shutil.which("espeak-ng") is not None or shutil.which("espeak") is not None

    def speak(self, text: str) -> str:
        if not text or not text.strip():
            return "tts:empty"

        binary = shutil.which("espeak-ng") or shutil.which("espeak")
        if binary is None:
            return "tts:unavailable"

        cmd = [binary, "-v", self.voice, "-s", str(self.rate), text]
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except OSError as exc:
            return f"tts:error:{exc}"

        if completed.returncode == 0:
            return "tts:spoken"
        stderr = (completed.stderr or "unknown_error").strip()
        return f"tts:error:{stderr}"

    def render_status(self) -> str:
        if not self.is_available():
            return "tts:unavailable backend=espeak_missing"
        return f"tts:ready engine=espeak voice={self.voice} rate={self.rate}"


if __name__ == "__main__":
    print(TTSEngine().render_status())
