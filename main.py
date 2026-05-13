"""Entry point for ImGui Forge Builder.

Run from the package folder:
    python main.py

Or from the workspace root:
    python imgui_forge_builder/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication


if __package__ in {None, ""}:
    package_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(package_dir.parent))
    from imgui_forge_builder.app import MainWindow
else:  # pragma: no cover
    from .app import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("ImGui Forge Builder")
    window = MainWindow()
    window.show()

    if "--smoke-test" in sys.argv:
        QTimer.singleShot(250, app.quit)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
