#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout
except ImportError as exc:  # pragma: no cover - handled by the GUI install flow
    raise RuntimeError("PySide6 is required for the Nova graphical uninstaller. Install it with `python3 -m pip install PySide6`.") from exc

PROJECT_ROOT = Path(__file__).resolve().parent
NOVA_DIR = PROJECT_ROOT / "nova-cortex"
RUNTIME_DIR = NOVA_DIR / ".runtime"
ENV_PATH = NOVA_DIR / ".env"
SYSTEMD_UNIT = Path("/etc/systemd/system/nova-cortex.service")
USER_SERVICE_DIR = Path.home() / ".config" / "systemd" / "user"
USER_SERVICE = USER_SERVICE_DIR / "nova-cortex.service"
USER_LISTENER = USER_SERVICE_DIR / "nova-listener.service"


def remove_path(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path) if path.is_dir() else path.unlink()


def uninstall_systemd() -> None:
    if not SYSTEMD_UNIT.exists():
        return
    subprocess.run(["sudo", "systemctl", "stop", "nova-cortex.service"], check=False)
    subprocess.run(["sudo", "systemctl", "disable", "nova-cortex.service"], check=False)
    subprocess.run(["sudo", "rm", "-f", str(SYSTEMD_UNIT)], check=False)
    subprocess.run(["sudo", "systemctl", "daemon-reload"], check=False)

    if USER_SERVICE.exists():
        USER_SERVICE.unlink()
    if USER_LISTENER.exists():
        USER_LISTENER.unlink()
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)


def uninstall_runtime() -> None:
    remove_path(RUNTIME_DIR)
    if ENV_PATH.exists():
        ENV_PATH.unlink()
    venv_dir = NOVA_DIR / ".venv"
    remove_path(venv_dir)


def uninstall_project() -> str:
    uninstall_systemd()
    uninstall_runtime()
    return "Nova runtime removed. User services were cleaned up. Any local Ollama install was left alone unless removed manually."


class NovaUninstallerDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Project Nova Uninstaller")
        self.resize(420, 180)

        self.label = QLabel("This will remove the Nova runtime and generated config from this project folder.")
        self.confirm_button = QPushButton("Remove Nova")
        self.confirm_button.clicked.connect(self.on_uninstall)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.cancel_button)
        row.addWidget(self.confirm_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addLayout(row)

    def on_uninstall(self) -> None:
        result = uninstall_project()
        QMessageBox.information(self, "Uninstall status", result)
        self.accept()


def _cli_mode() -> int:
    print(uninstall_project())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Graphical uninstaller for Project Nova")
    parser.add_argument("--headless", action="store_true", help="Run in non-GUI CLI mode")
    args = parser.parse_args()

    if args.headless:
        return _cli_mode()

    app = QApplication.instance() or QApplication(sys.argv)
    dialog = NovaUninstallerDialog()
    dialog.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
