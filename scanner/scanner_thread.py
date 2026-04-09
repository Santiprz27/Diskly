"""ScannerThread — non-blocking QThread that runs the disk scan pipeline.

Signals emitted:
  progress(count: int, elapsed: float)  — periodic progress update
  scan_complete(root: DirNode)           — scan finished successfully
  error(msg: str)                        — scan failed with an error message
"""

from __future__ import annotations

import time
import logging

from PyQt6.QtCore import QThread, pyqtSignal

from scanner.mft_scanner import scan_drive
from scanner.dir_trie import DirNode
from utils.elevation import is_admin

log = logging.getLogger(__name__)


class ScannerThread(QThread):
    progress = pyqtSignal(int, float)   # (entry_count, elapsed_seconds)
    scan_complete = pyqtSignal(object)  # (root DirNode)
    error = pyqtSignal(str)

    def __init__(self, drive_letter: str, parent=None):
        super().__init__(parent)
        self.drive_letter = drive_letter.upper().rstrip(":\\")
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    # ------------------------------------------------------------------ #

    def run(self) -> None:
        t0    = time.perf_counter()
        count = 0
        admin = is_admin()

        def on_progress(n: int) -> None:
            nonlocal count
            count   = n
            elapsed = time.perf_counter() - t0
            self.progress.emit(n, elapsed)

        try:
            root = DirNode(name=f"{self.drive_letter}:\\")

            log.info(
                "Starting scan — drive=%s admin=%s",
                self.drive_letter, admin,
            )

            for parts, size, is_dir in scan_drive(
                self.drive_letter,
                admin=admin,
                progress_cb=on_progress,
            ):
                if self._cancelled:
                    return
                if parts:
                    root.insert(parts, size, is_dir)
                count += 1

        except Exception as exc:
            log.exception("Scan error")
            self.error.emit(str(exc))
            return

        log.info("Calculating total sizes…")
        root.accumulate()

        elapsed = time.perf_counter() - t0
        log.info(
            "Scan complete: %d entries in %.2fs (admin=%s)",
            count, elapsed, admin,
        )
        self.scan_complete.emit(root)
