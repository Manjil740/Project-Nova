from __future__ import annotations

from pathlib import Path

from nova.ui.state_engine import StateEngine

try:
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtWidgets import QApplication, QLabel, QWidget
except ImportError as exc:  # pragma: no cover - import is validated in the real environment
    raise RuntimeError(
        "PySide6 is required for the Nova overlay. Install it with `python3 -m pip install PySide6`."
    ) from exc


class NovaOverlay(QWidget):
    """Transparent, frameless overlay for Linux desktops.

    The overlay is intentionally a presentation-layer component only. It reads
    status from the live Nova IPC socket via ``StateEngine`` and never owns the
    core execution logic or state machine.
    """

    def __init__(self, project_root: Path | str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state_engine = StateEngine(project_root=Path(project_root))

        self.label = QLabel("Listening…", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(
            "color: #edf6ff; font-size: 18px; font-weight: 600; background: rgba(10, 14, 24, 0.45); "
            "border: 1px solid rgba(255,255,255,0.22); border-radius: 18px; padding: 16px 24px;"
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.resize(320, 90)
        self.setStyleSheet("background: transparent;")

        self.state_engine.subscribe(self._on_status_update)
        self._timer = QTimer(self)
        self._timer.setInterval(1500)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start()

        self._refresh_status()

    def _on_status_update(self, status: str) -> None:
        self.label.setText(status)

    def _refresh_status(self) -> None:
        raw = self.state_engine.request_status("status")
        self.label.setText(raw)

    def show_overlay(self) -> None:
        self.show()


def main() -> None:
    app = QApplication.instance() or QApplication([])
    overlay = NovaOverlay(Path(__file__).resolve().parents[2])
    overlay.show_overlay()
    app.exec()


if __name__ == "__main__":
    main()
