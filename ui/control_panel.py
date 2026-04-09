"""ControlPanel — left sidebar.

Includes: drive selector, admin badge, scan/stop, animated progress,
search with result count, breadcrumbs, top-10 files table, stats footer.
"""

from __future__ import annotations

import logging

import psutil

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QProgressBar, QFrame, QScrollArea,
    QSizePolicy, QTableWidget, QListWidget, QListWidgetItem,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PyQt6.QtGui import QFont, QPixmap

from scanner.dir_trie import DirNode
from utils.elevation import is_admin
from utils.format_bytes import format_bytes, format_count

log = logging.getLogger(__name__)

_ADMIN = is_admin()


class BreadcrumbBar(QWidget):
    """Clickable path breadcrumbs."""
    segment_clicked = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

    def set_path(self, abs_path: list[str], root_label: str = "") -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        segments = ([root_label] if root_label else []) + list(abs_path)

        for i, seg in enumerate(segments):
            btn = QPushButton(seg)
            btn.setObjectName("breadcrumb")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(26)
            btn.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            # Make the last segment highlighted
            if i == len(segments) - 1:
                btn.setStyleSheet(
                    "QPushButton#breadcrumb { color: #ff6044; font-weight: 700; }"
                )

            target = list(abs_path[:i]) if i > 0 else []

            def _on_click(checked=False, t=target):
                self.segment_clicked.emit(t)

            btn.clicked.connect(_on_click)
            self._layout.addWidget(btn)

            if i < len(segments) - 1:
                sep = QLabel("›")
                sep.setObjectName("breadcrumb-sep")
                sep.setFixedWidth(14)
                sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._layout.addWidget(sep)

        self._layout.addStretch()


class ControlPanel(QWidget):
    scan_requested     = pyqtSignal(str)
    scan_cancelled     = pyqtSignal()
    navigate_requested = pyqtSignal(object)
    search_changed     = pyqtSignal(str)
    navigate_to_result = pyqtSignal(object)  # path_parts to navigate on search click

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(310)
        self.setObjectName("ControlPanel")

        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._emit_search)

        # Animated ellipsis timer
        self._dot_timer = QTimer()
        self._dot_timer.setInterval(500)
        self._dot_timer.timeout.connect(self._tick_dots)
        self._dot_count = 0

        # Stores (node, path_parts) for current search results
        self._search_results: list = []

        self._build_ui()
        self._populate_drives()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("PanelScroll")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 22, 16, 16)
        layout.setSpacing(0)

        # ── Title ──
        logo_row = QHBoxLayout()
        logo_row.setSpacing(12)
        
        title_lbl = QLabel("Diskly")
        title_lbl.setObjectName("logo-title")
        
        logo_row.addWidget(title_lbl)
        logo_row.addStretch()
        
        layout.addLayout(logo_row)

        layout.addSpacing(3)
        sub = QLabel("Analizador de Espacio en Disco")
        sub.setObjectName("logo-subtitle")
        layout.addWidget(sub)

        layout.addSpacing(20)
        layout.addWidget(self._divider())

        # ── Drive selector ──
        layout.addSpacing(16)
        layout.addWidget(self._section("Unidad"))
        layout.addSpacing(7)
        self._drive_combo = QComboBox()
        self._drive_combo.setObjectName("DriveCombo")
        # Limit minimum width to the character count, not the longest item text.
        # Without this, a long drive label forces the scroll area wider than the panel.
        self._drive_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self._drive_combo.setMinimumContentsLength(20)
        layout.addWidget(self._drive_combo)
        layout.addSpacing(10)

        # Scan / Stop row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._scan_btn = QPushButton("Analizar")
        self._scan_btn.setObjectName("ScanBtn")
        self._scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._scan_btn.clicked.connect(self._on_scan_clicked)
        self._stop_btn = QPushButton("✕")
        self._stop_btn.setObjectName("StopBtn")
        self._stop_btn.setFixedWidth(44)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.setToolTip("Detener análisis")
        self._stop_btn.clicked.connect(self.scan_cancelled)
        btn_row.addWidget(self._scan_btn)
        btn_row.addWidget(self._stop_btn)
        layout.addLayout(btn_row)
        layout.addSpacing(10)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("ScanProgress")
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)
        layout.addSpacing(4)

        # Status label
        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("status-label")
        self._status_lbl.setWordWrap(True)
        layout.addWidget(self._status_lbl)

        layout.addSpacing(16)
        layout.addWidget(self._divider())

        # ── Search ──
        layout.addSpacing(16)
        layout.addWidget(self._section("Buscar archivo"))
        layout.addSpacing(7)
        self._search_box = QLineEdit()
        self._search_box.setObjectName("SearchBox")
        self._search_box.setPlaceholderText("nombre o extensión, ej: .mp4")
        self._search_box.setClearButtonEnabled(True)
        self._search_box.textChanged.connect(self._on_search_changed)
        layout.addWidget(self._search_box)
        layout.addSpacing(4)
        self._search_result_lbl = QLabel("")
        self._search_result_lbl.setObjectName("SearchResultLabel")
        layout.addWidget(self._search_result_lbl)
        layout.addSpacing(4)

        # Results list — hidden until there are search results
        self._results_list = QListWidget()
        self._results_list.setObjectName("SearchResultsList")
        self._results_list.setFixedHeight(220)
        self._results_list.setVisible(False)
        self._results_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self._results_list.itemClicked.connect(self._on_result_clicked)
        layout.addWidget(self._results_list)

        layout.addSpacing(16)
        layout.addWidget(self._divider())

        # ── Breadcrumbs ──
        layout.addSpacing(16)
        layout.addWidget(self._section("Ruta actual"))
        layout.addSpacing(7)

        bc_scroll = QScrollArea()
        bc_scroll.setWidgetResizable(True)
        bc_scroll.setFixedHeight(36)
        bc_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        bc_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        bc_scroll.setFrameShape(QFrame.Shape.NoFrame)
        bc_scroll.setObjectName("BreadcrumbScroll")
        self._breadcrumbs = BreadcrumbBar()
        self._breadcrumbs.segment_clicked.connect(self.navigate_requested)
        bc_scroll.setWidget(self._breadcrumbs)
        layout.addWidget(bc_scroll)

        layout.addSpacing(7)
        self._back_btn = QPushButton("← Atrás")
        self._back_btn.setObjectName("BackBtn")
        self._back_btn.setEnabled(False)
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.clicked.connect(self._on_back_clicked)
        layout.addWidget(self._back_btn)

        layout.addSpacing(16)
        layout.addWidget(self._divider())

        # ── Top 10 archivos más pesados ──
        layout.addSpacing(16)
        layout.addWidget(self._section("Archivos más pesados"))
        layout.addSpacing(7)

        self._top_table = QTableWidget(0, 2)
        self._top_table.setObjectName("TopTable")
        self._top_table.setHorizontalHeaderLabels(["Archivo", "Tamaño"])
        self._top_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._top_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Fixed
        )
        self._top_table.horizontalHeader().resizeSection(1, 72)
        self._top_table.verticalHeader().setVisible(False)
        self._top_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._top_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._top_table.setAlternatingRowColors(True)
        self._top_table.setShowGrid(False)
        self._top_table.setFixedHeight(220)
        self._top_table.setToolTip("Los 10 archivos más pesados en la carpeta actual")
        layout.addWidget(self._top_table)



        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

        # ── Stats footer ──
        footer = QWidget()
        footer.setObjectName("StatsFooter")
        fl = QVBoxLayout(footer)
        fl.setContentsMargins(16, 10, 16, 12)
        fl.setSpacing(5)

        self._stats_total = QLabel("—")
        self._stats_files = QLabel("—")
        self._stats_time  = QLabel("—")

        for key, val, prop in [
            ("Tamaño total", self._stats_total, True),
            ("Archivos",     self._stats_files, False),
            ("Tiempo",       self._stats_time,  False),
        ]:
            row = QHBoxLayout()
            k = QLabel(key)
            k.setObjectName("stats-key")
            row.addWidget(k)
            row.addStretch()
            row.addWidget(val)
            val.setObjectName("stats-value")
            if prop:
                val.setProperty("highlight", True)
            fl.addLayout(row)

        fl.addSpacing(5)
        ver = QLabel(f"Diskly v1.0.0  {'| Admin' if _ADMIN else '| Usuario'}")
        ver.setObjectName("version-label")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fl.addWidget(ver)
        outer.addWidget(footer)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        return line

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("section-label")
        return lbl

    def _populate_drives(self) -> None:
        self._drive_combo.clear()
        for p in psutil.disk_partitions(all=False):
            letter = p.device.rstrip(":\\")
            try:
                usage = psutil.disk_usage(p.mountpoint)
                used_pct = int(usage.percent)
                label = (
                    f"{letter}:\\  —  "
                    f"{format_bytes(usage.used)} / {format_bytes(usage.total)}"
                    f"  ({p.fstype})  {used_pct}%"
                )
            except (PermissionError, OSError):
                label = f"{letter}:\\"
            self._drive_combo.addItem(label, letter)

    def _tick_dots(self) -> None:
        self._dot_count = (self._dot_count + 1) % 4
        dots = "." * self._dot_count
        current = self._status_lbl.text()
        # Keep number portion, update dots
        base = current.rstrip(".").rstrip()
        self._status_lbl.setText(base + dots)

    # ------------------------------------------------------------------ #
    # Handlers
    # ------------------------------------------------------------------ #

    def _on_scan_clicked(self) -> None:
        letter = self._drive_combo.currentData()
        if letter:
            self.scan_requested.emit(letter)

    def _on_search_changed(self) -> None:
        self._search_timer.stop()
        self._search_timer.start(350)

    def _emit_search(self) -> None:
        q = self._search_box.text().strip()
        self.search_changed.emit(q)
        if not q:
            self._search_result_lbl.setText("")

    def _on_back_clicked(self) -> None:
        self.navigate_requested.emit(None)

    def _on_result_clicked(self, item: QListWidgetItem) -> None:
        """Navigate treemap to the folder/file the user clicked in search results."""
        path_parts = item.data(Qt.ItemDataRole.UserRole)
        if path_parts is not None:
            self.navigate_to_result.emit(path_parts)
    # ------------------------------------------------------------------ #
    # Public update methods (called from MainWindow)
    # ------------------------------------------------------------------ #

    def set_scanning(self, scanning: bool) -> None:
        self._scan_btn.setEnabled(not scanning)
        self._stop_btn.setEnabled(scanning)
        self._drive_combo.setEnabled(not scanning)
        self._progress_bar.setVisible(scanning)
        if scanning:
            self._dot_timer.start()
        else:
            self._dot_timer.stop()

    def update_progress(self, count: int, elapsed: float) -> None:
        mode = "rápido" if _ADMIN else "normal"
        rate = int(count / elapsed) if elapsed > 0 else 0
        self._status_lbl.setText(
            f"Analizando ({mode})  ·  {format_count(count)} archivos  ·  {elapsed:.0f}s"
        )

    def update_stats(self, root: DirNode, elapsed: float) -> None:
        self._stats_total.setText(format_bytes(root.total_size))
        self._stats_files.setText(format_count(root.total_files))
        self._stats_time.setText(f"{elapsed:.1f}s")
        self._status_lbl.setText("Análisis completado")

    def update_breadcrumbs(self, abs_path: list[str], root_label: str = "") -> None:
        self._breadcrumbs.set_path(abs_path, root_label)
        self._back_btn.setEnabled(len(abs_path) > 0)

    def update_top_files(self, files: list[tuple[str, int, list[str]]]) -> None:
        self._top_table.setRowCount(0)
        for i, (name, size, _) in enumerate(files[:10]):
            self._top_table.insertRow(i)
            self._top_table.setRowHeight(i, 24)
            name_item = QTableWidgetItem(name)
            name_item.setToolTip(name)
            size_item = QTableWidgetItem(format_bytes(size))
            size_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self._top_table.setItem(i, 0, name_item)
            self._top_table.setItem(i, 1, size_item)

    def show_search_results(
        self,
        results: list,    # list of (DirNode, list[str])
        query: str,
    ) -> None:
        """Populate the search results list and show/hide it as needed."""
        self._search_results = results
        self._results_list.clear()

        if not query:
            self._search_result_lbl.setText("")
            self._results_list.setVisible(False)
            return

        if not results:
            self._search_result_lbl.setText("Sin resultados")
            self._results_list.setVisible(False)
            return

        count = len(results)
        self._search_result_lbl.setText(
            f"{count} resultado{'s' if count != 1 else ''} — haz clic para navegar"
        )

        for node, path_parts in results:
            is_dir = node.is_dir
            icon   = "📁" if is_dir else "📄"
            size   = format_bytes(node.total_size)

            # Parent path string for display
            parent_parts = path_parts[:-1]
            parent_str   = " / ".join(parent_parts) if parent_parts else "/"

            item = QListWidgetItem(f"{icon}  {node.name}")
            item.setToolTip(f"{' / '.join(path_parts)}  ({size})")

            # Navigate to parent dir for files, to self for dirs
            nav_path = path_parts if is_dir else parent_parts
            item.setData(Qt.ItemDataRole.UserRole, nav_path)

            # Secondary text via status tip (shown in tooltip overflow)
            item.setStatusTip(f"{parent_str}  •  {size}")

            self._results_list.addItem(item)

        self._results_list.setVisible(True)

    # kept for backward compat
    def update_search_results(self, count: int, query: str) -> None:
        self._search_result_lbl.setText(
            f"{count} resultado{'s' if count != 1 else ''}" if query and count else ""
        )

    def set_error(self, msg: str) -> None:
        self._status_lbl.setText(f"Error: {msg}")

    def current_drive(self) -> str:
        return self._drive_combo.currentData() or ""
