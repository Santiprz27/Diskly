"""Diskly — Main entry point.

Launch sequence:
  1. Check for Administrator privileges → request via UAC if missing
  2. Initialize QApplication with dark stylesheet
  3. Show MainWindow
  4. Start event loop
"""

import sys
import os
import logging

# ── Ensure project root is on sys.path ────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("diskly")

# ── PyQt6 imports ─────────────────────────────────────────────────────────
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont

# ── App setup ─────────────────────────────────────────────────────────────

def load_stylesheet() -> str:
    qss_path = os.path.join(ROOT, "styles", "app.qss")
    try:
        with open(qss_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        log.warning("Stylesheet not found: %s", qss_path)
        return ""


def main() -> int:
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Diskly")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Diskly")

    # Default font
    font = QFont("Segoe UI", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferDefaultHinting)
    app.setFont(font)

    # Dark stylesheet
    qss = load_stylesheet()
    if qss:
        app.setStyleSheet(qss)

    # Icon (optional — won't crash if missing)
    icon_path = os.path.join(ROOT, "assets", "diskly_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # ── Admin check ──
    from utils.elevation import is_admin, request_elevation

    if not is_admin():
        log.info("Not running as Administrator — requesting UAC elevation…")
        request_elevation()
        # request_elevation() calls sys.exit(0) after spawning the elevated
        # process, so we never reach the lines below in the non-admin process.

    # ── Main window ──
    from ui.main_window import MainWindow

    window = MainWindow()
    window.show()

    log.info("Diskly started (admin=%s)", is_admin())
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
