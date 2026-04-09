"""MainWindow — top-level QMainWindow."""

from __future__ import annotations

import time
import logging
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout

from scanner.dir_trie import DirNode
from scanner.scanner_thread import ScannerThread
from ui.control_panel import ControlPanel
from ui.treemap_view import TreemapView
from utils.elevation import is_admin

log = logging.getLogger(__name__)

_ADMIN = is_admin()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._root: Optional[DirNode]        = None
        self._scanner: Optional[ScannerThread] = None
        self._scan_start: float              = 0.0
        self._root_label: str               = ""

        mode = "Admin" if _ADMIN else "Usuario"
        self.setWindowTitle(f"Diskly — Analizador de Espacio en Disco  [{mode}]")
        self.resize(1360, 860)
        self.setMinimumSize(960, 640)

        self._build_ui()

    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Left panel
        self._panel = ControlPanel()
        self._panel.scan_requested.connect(self._start_scan)
        self._panel.scan_cancelled.connect(self._cancel_scan)
        self._panel.navigate_requested.connect(self._navigate_from_panel)
        self._panel.search_changed.connect(self._on_search)

        # Right chart
        self._chart = TreemapView()
        self._chart.navigated.connect(self._on_chart_navigated)
        self._panel.navigate_to_result.connect(self._chart.navigate_to)

        root_layout.addWidget(self._panel)

        divider = QWidget()
        divider.setFixedWidth(1)
        divider.setObjectName("VertDivider")
        root_layout.addWidget(divider)

        root_layout.addWidget(self._chart, stretch=1)

    # ------------------------------------------------------------------ #
    # Scan lifecycle
    # ------------------------------------------------------------------ #

    def _start_scan(self, drive: str) -> None:
        if self._scanner and self._scanner.isRunning():
            self._scanner.cancel()
            self._scanner.wait(2000)

        self._root_label = f"{drive}:\\"
        self._scan_start = time.perf_counter()
        self._panel.set_scanning(True)
        self._panel.update_breadcrumbs([], root_label=self._root_label)

        mode = "Admin" if _ADMIN else "Usuario"
        self.setWindowTitle(
            f"Diskly — Escaneando {drive}:\\…  [{mode}]"
        )

        self._scanner = ScannerThread(drive)
        self._scanner.progress.connect(self._on_progress)
        self._scanner.scan_complete.connect(self._on_scan_complete)
        self._scanner.error.connect(self._on_scan_error)
        self._scanner.start()

    def _cancel_scan(self) -> None:
        if self._scanner:
            self._scanner.cancel()
        self._panel.set_scanning(False)
        self._panel.set_error("Análisis cancelado")
        mode = "Admin" if _ADMIN else "Usuario"
        self.setWindowTitle(f"Diskly — Analizador de Espacio en Disco  [{mode}]")

    # ------------------------------------------------------------------ #
    # Scanner signals
    # ------------------------------------------------------------------ #

    def _on_progress(self, count: int, elapsed: float) -> None:
        self._panel.update_progress(count, elapsed)

    def _on_scan_complete(self, root: DirNode) -> None:
        self._root = root
        elapsed = time.perf_counter() - self._scan_start
        self._panel.set_scanning(False)
        self._panel.update_stats(root, elapsed)
        self._panel.update_breadcrumbs([], root_label=self._root_label)

        # Update window title with result
        from utils.format_bytes import format_bytes
        mode = "Admin" if _ADMIN else "Usuario"
        self.setWindowTitle(
            f"Diskly — {self._root_label}  {format_bytes(root.total_size)}  "
            f"[{mode}  {elapsed:.1f}s]"
        )

        self._chart.load_root(root)
        log.info("Scan done: %s, %.2fs, admin=%s", root, elapsed, _ADMIN)

    def _on_scan_error(self, msg: str) -> None:
        self._panel.set_scanning(False)
        self._panel.set_error(msg)
        mode = "Admin" if _ADMIN else "Usuario"
        self.setWindowTitle(f"Diskly — Error  [{mode}]")

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #

    def _navigate_from_panel(self, path_parts) -> None:
        if self._root is None:
            return
        if path_parts is None:
            self._chart.navigate_back()
        else:
            self._chart.navigate_to(path_parts)

    def _on_chart_navigated(self, abs_path: list, node: DirNode) -> None:
        self._panel.update_breadcrumbs(abs_path, root_label=self._root_label)
        top = node.top_files(10)
        self._panel.update_top_files(top)

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #

    def _on_search(self, query: str) -> None:
        if not self._root:
            return
        if not query:
            self._panel.show_search_results([], "")
            self._chart.set_search_results(None)
            return
            
        matches_with_paths = self._root.search_with_paths(query, max_results=200)
        self._panel.show_search_results(matches_with_paths, query)
        self._chart.set_search_results(matches_with_paths)
        if matches_with_paths:
            best_node, _ = matches_with_paths[0]
            log.info(
                "Search '%s' → %d matches, best: %s",
                query, len(matches_with_paths), best_node.name
            )

    # ------------------------------------------------------------------ #

    def closeEvent(self, event) -> None:
        if self._scanner and self._scanner.isRunning():
            self._scanner.cancel()
            self._scanner.wait(3000)
        super().closeEvent(event)
