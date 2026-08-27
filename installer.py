#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout
except ImportError as exc:  # pragma: no cover - handled by the GUI install flow
    raise RuntimeError("PySide6 is required for the Nova graphical installer. Install it with `python3 -m pip install PySide6`.") from exc

PROJECT_ROOT = Path(__file__).resolve().parent
NOVA_DIR = PROJECT_ROOT / "nova-cortex"
ENV_PATH = NOVA_DIR / ".env"

BACKENDS = ["ollama", "llama.cpp", "custom"]
MODELS = [
    "qwen2.5-coder:3b",
    "llama3.2:3b",
    "mistral:7b",
    "custom",
]


def write_env(backend: str, model: str, generate_env: bool) -> None:
    if not generate_env:
        return

    base_url = "http://localhost:11434"
    if backend == "llama.cpp":
        base_url = "http://localhost:8080"
    elif backend == "custom":
        base_url = "http://localhost:11434"

    env_lines = [
        f"LLM_PROVIDER={backend}",
        f"LLM_MODEL={model}",
        f"LLM_BASE_URL={base_url}",
        "EMBEDDING_MODEL=nomic-embed-text",
        "SANDBOX_ENABLED=true",
        "MEMORY_ENABLED=true",
        "CHROMA_DB_PATH=~/.local/share/nova/chroma_db",
        "EMBEDDING_BATCH_SIZE=8",
        "DATA_DIR=~/.local/share/nova",
    ]

    NOVA_DIR.mkdir(parents=True, exist_ok=True)
    ENV_PATH.write_text("\n".join(env_lines) + "\n", encoding="utf-8")


def install_local_package() -> None:
    subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(NOVA_DIR)], check=False)


def ensure_user_service() -> None:
    service_dir = Path.home() / ".config" / "systemd" / "user"
    service_dir.mkdir(parents=True, exist_ok=True)
    template = PROJECT_ROOT / "services" / "nova-cortex.service"
    target = service_dir / "nova-cortex.service"
    if template.exists():
        target.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")

    listener_template = PROJECT_ROOT / "services" / "nova-listener.service"
    listener_target = service_dir / "nova-listener.service"
    if listener_template.exists():
        listener_target.write_text(listener_template.read_text(encoding="utf-8"), encoding="utf-8")

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)


def install_backend(backend: str, model: str) -> None:
    if backend == "ollama":
        if subprocess.run(["bash", "-lc", "command -v ollama >/dev/null 2>&1"], check=False).returncode != 0:
            print("Ollama is not installed yet. Install it with: curl -fsSL https://ollama.com/install.sh | sh")
            return
        if model and model != "custom":
            subprocess.run(["ollama", "pull", model], check=False)
        return

    if backend == "llama.cpp":
        if subprocess.run(["bash", "-lc", "command -v llama-server >/dev/null 2>&1 || command -v llama-cli >/dev/null 2>&1"], check=False).returncode != 0:
            print("llama.cpp is not installed yet. Install it from the llama.cpp project before continuing.")
            return
        return


def run_post_install_checks() -> str:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(NOVA_DIR)
    checks = [
        [sys.executable, "-m", "compileall", str(NOVA_DIR / "nova")],
        [
            sys.executable,
            "-c",
            "from nova.core.config import NovaConfig; from nova.core.platform import SystemProfile; from nova.tools.registry import ToolRouter; from pathlib import Path; print('nova_packaging_smoke_ok')",
        ],
    ]
    for cmd in checks:
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return f"post_install_failed: {result.stderr.strip() or result.stdout.strip() or 'unknown_error'}"
    return "post_install_checks=passed"


def run_install(backend: str, model: str, generate_env: bool) -> str:
    if generate_env:
        write_env(backend, model, generate_env=True)
    install_local_package()
    install_backend(backend, model)
    ensure_user_service()
    checks = run_post_install_checks()
    return (
        f"backend={backend} model={model} env_written={str(generate_env).lower()} "
        f"project_root={PROJECT_ROOT} {checks}"
    )


class NovaInstallerDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Project Nova Installer")
        self.resize(440, 250)

        self.backend_combo = QComboBox()
        self.backend_combo.addItems(BACKENDS)
        self.model_combo = QComboBox()
        self.model_combo.addItems(MODELS)
        self.env_checkbox = QCheckBox("Generate .env configuration")
        self.env_checkbox.setChecked(True)

        self.run_button = QPushButton("Install Nova")
        self.run_button.clicked.connect(self.on_install)

        form = QFormLayout()
        form.addRow("Backend", self.backend_combo)
        form.addRow("Model", self.model_combo)
        form.addRow("", self.env_checkbox)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Project Nova is a local Linux AI assistant. This GUI sets up the backend and config."))
        layout.addLayout(form)
        layout.addLayout(self._button_row())

    def _button_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.run_button)
        return row

    def on_install(self) -> None:
        backend = self.backend_combo.currentText()
        model = self.model_combo.currentText()
        generate_env = self.env_checkbox.isChecked()
        result = run_install(backend, model, generate_env)
        QMessageBox.information(self, "Installation status", result)


def _cli_mode(args: argparse.Namespace) -> int:
    backend = args.backend or "ollama"
    model = args.model or "qwen2.5-coder:3b"
    generate_env = args.env or True
    result = run_install(backend, model, generate_env)
    print(result)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Graphical installer for Project Nova")
    parser.add_argument("--backend", choices=BACKENDS, default="ollama")
    parser.add_argument("--model", default="qwen2.5-coder:3b")
    parser.add_argument("--env", action="store_true", default=True, help="Write .env configuration")
    parser.add_argument("--no-env", action="store_false", dest="env", help="Skip .env generation")
    parser.add_argument("--headless", action="store_true", help="Run in non-GUI CLI mode")
    args = parser.parse_args()

    if args.headless:
        return _cli_mode(args)

    app = QApplication.instance() or QApplication(sys.argv)
    dialog = NovaInstallerDialog()
    dialog.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
