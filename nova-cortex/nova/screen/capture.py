from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ScreenCapture:
    """Linux-native screen capture utility.

    This follows the optional Stage 9B roadmap and deliberately keeps all image
    processing local-only. It uses `grim` + `slurp` on Wayland and `scrot`
    (with xdg-desktop-portal as an alternative) on X11 when available.
    """

    output_path: str | Path = "/tmp/nova-screenshot.png"
    display_type: str = "unknown"

    def detect_environment(self) -> str:
        if os.environ.get("WAYLAND_DISPLAY"):
            self.display_type = "wayland"
        elif os.environ.get("DISPLAY"):
            self.display_type = "x11"
        else:
            self.display_type = "unknown"
        return self.display_type

    def is_available(self) -> bool:
        detection = self.detect_environment()
        if detection == "wayland":
            return shutil.which("grim") is not None and shutil.which("slurp") is not None
        if detection == "x11":
            return shutil.which("scrot") is not None or shutil.which("xdg-desktop-portal") is not None
        return False

    def capture(self) -> str:
        detection = self.detect_environment()
        out_path = str(Path(self.output_path).expanduser())
        output_dir = Path(out_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        if detection == "wayland":
            if shutil.which("grim") is None or shutil.which("slurp") is None:
                return "screen_capture:unavailable wayland_tools_missing"
            command = ["bash", "-lc", f"grim -g \"$(slurp)\" '{out_path}' 2>/dev/null"]
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            if completed.returncode == 0 and Path(out_path).exists():
                return f"screen_capture:captured path={out_path} backend=grim_slurp"
            return "screen_capture:error wayland_capture_failed"

        if detection == "x11":
            if shutil.which("scrot") is not None:
                completed = subprocess.run(["scrot", out_path], capture_output=True, text=True, check=False)
                if completed.returncode == 0 and Path(out_path).exists():
                    return f"screen_capture:captured path={out_path} backend=scrot"
                return "screen_capture:error x11_capture_failed"
            if shutil.which("xdg-desktop-portal") is not None:
                return f"screen_capture:portal_available path={out_path} backend=xdg_desktop_portal"
            return "screen_capture:unavailable x11_tools_missing"

        return "screen_capture:unavailable display_unknown"

    def render_status(self) -> str:
        detection = self.detect_environment()
        if not self.is_available():
            return f"screen:unavailable env={detection}"
        return f"screen:ready env={detection} path={self.output_path}"
