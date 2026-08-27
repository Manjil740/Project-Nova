from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SystemProfile:
    distro_id: str = "unknown"
    distro_name: str = "Unknown Linux"
    distro_like: str = ""

    @classmethod
    def detect(cls, os_release_path: Path | None = None) -> "SystemProfile":
        release_path = os_release_path or Path("/etc/os-release")
        fields = cls._parse_os_release(release_path)
        return cls(
            distro_id=fields.get("ID", "unknown").strip('"').strip() or "unknown",
            distro_name=fields.get("PRETTY_NAME", "Unknown Linux").strip('"').strip() or "Unknown Linux",
            distro_like=fields.get("ID_LIKE", "").strip('"').strip(),
        )

    @staticmethod
    def _parse_os_release(release_path: Path) -> dict[str, str]:
        if not release_path.exists():
            return {}

        fields: dict[str, str] = {}
        for raw_line in release_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            fields[key.strip()] = value.strip()
        return fields

    def short_name(self) -> str:
        if self.distro_id != "unknown":
            return self.distro_id
        return self.distro_name.lower().replace(" ", "_")

    def render(self) -> str:
        return f"system:distro_id={self.distro_id} distro_name={self.distro_name} distro_like={self.distro_like or 'unknown'}"