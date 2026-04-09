"""TreemapView — Native QPainter squarified treemap visualizer.

UX improvements (v2):
  - Rich empty state with icon + hint text.
  - Path header bar drawn on the canvas itself (always visible).
  - Pointer cursor on directories, arrow cursor on files.
  - Hover overlay with subtle glow.
  - Double-click to navigate into a directory.
"""

from __future__ import annotations

import logging
from typing import Optional, Any
import time

from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF, QRect
from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QMouseEvent, QPaintEvent,
    QFont, QFontMetrics, QLinearGradient, QPixmap,
)

from scanner.dir_trie import DirNode
from utils.format_bytes import format_bytes
from utils.color_map import get_color_for_file
from utils.squarify import squarify_dirnode

log = logging.getLogger(__name__)

# ─── Design tokens ────────────────────────────────────────────────────────────
_BG         = QColor("#111211")
_BG_HEADER  = QColor("#181918")
_ACCENT     = QColor("#e05a38")
_TEXT       = QColor("#dcdcda")
_TEXT_MUTED  = QColor("#535553")
_BORDER      = QColor("#222422")
_HEADER_H    = 30        # px — altura del header de ruta


class TreemapView(QWidget):
    """High-performance native treemap with path header and UX polish."""

    navigated = pyqtSignal(object, object)   # (abs_path_parts, node)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.ArrowCursor)

        self._root: Optional[DirNode]         = None
        self._nav_stack: list[list[str]]      = [[]]
        self._current_node: Optional[DirNode] = None

        self._boxes: list[dict[str, Any]]     = []
        self._hovered_box: Optional[dict]     = None
        self._cached_pixmap: Optional[QPixmap] = None

        self._font        = QFont("Segoe UI", 8)
        self._header_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        self._path_font   = QFont("Segoe UI", 9)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def load_root(self, root: DirNode) -> None:
        self._root = root
        self._nav_stack = [[]]
        self._render_current()

    def navigate_to(self, path_parts: list[str]) -> None:
        if self._root is None:
            return
        node = self._root.get_node(path_parts)
        if node is None:
            log.warning("navigate_to: node not found for %s", path_parts)
            return
        if not self._nav_stack or self._nav_stack[-1] != path_parts:
            self._nav_stack.append(list(path_parts))
        self._current_node = node
        self._cached_pixmap = None
        self._recompute_layout()
        self.navigated.emit(list(path_parts), node)

    def navigate_back(self) -> None:
        if len(self._nav_stack) > 1:
            self._nav_stack.pop()
            self._cached_pixmap = None
            self._render_current()

    def current_node(self) -> Optional[DirNode]:
        return self._current_node

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #

    def _render_current(self) -> None:
        if self._root is None:
            self._current_node = None
            self._boxes = []
            self._cached_pixmap = None
            self.update()
            return

        path = self._nav_stack[-1] if self._nav_stack else []
        node = self._root.get_node(path)
        if node:
            self._current_node = node
            self._cached_pixmap = None
            self._recompute_layout()
            self.navigated.emit(list(path), node)

    def _recompute_layout(self) -> None:
        if not self._current_node:
            self._boxes = []
            self._cached_pixmap = None
            self.update()
            return

        w, h = self.width(), self.height()
        content_h = h - _HEADER_H
        if w <= 1 or content_h <= 1:
            return

        t0 = time.perf_counter()
        current_path = self._nav_stack[-1] if self._nav_stack else []
        self._boxes = squarify_dirnode(
            self._current_node, 0, _HEADER_H, w, content_h,
            pad=2.0, path_parts=current_path,
        )
        log.debug(
            "Layout: %d boxes in %.1f ms",
            len(self._boxes), (time.perf_counter() - t0) * 1000,
        )
        self._cached_pixmap = None
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._cached_pixmap = None
        self._recompute_layout()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._recompute_layout()

    # ------------------------------------------------------------------ #
    # Painting
    # ------------------------------------------------------------------ #

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Background
        painter.fillRect(self.rect(), _BG)

        # Empty state
        if not self._boxes:
            self._draw_header(painter, [])
            self._draw_empty_state(painter)
            return

        # Content pixmap (cached)
        if self._cached_pixmap is None or self._cached_pixmap.size() != self.size():
            self._render_to_pixmap()
        painter.drawPixmap(0, 0, self._cached_pixmap)

        # Hover overlay (drawn live — not cached)
        if self._hovered_box:
            hx, hy, hw, hh = self._hovered_box["rect"]
            painter.fillRect(QRectF(hx, hy, hw, hh), QColor(255, 255, 255, 28))
            painter.setPen(QPen(QColor(255, 255, 255, 100), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(hx, hy, hw, hh))

    def _render_to_pixmap(self) -> None:
        self._cached_pixmap = QPixmap(self.size())
        self._cached_pixmap.fill(_BG)

        painter = QPainter(self._cached_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setFont(self._font)
        fm = QFontMetrics(self._font)

        for box in self._boxes:
            x, y, w, h = box["rect"]
            geom = QRectF(x, y, w, h)
            is_dir = box.get("is_dir", False)
            depth  = box.get("depth", 0)
            color  = get_color_for_file(box["name"], is_dir, depth)

            # ── Fill ───────────────────────────────────────────────────
            if is_dir:
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(QColor(0, 0, 0, 60), 1))
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                if w > 6 and h > 6:
                    grad = QLinearGradient(x, y, x + w, y + h)
                    grad.setColorAt(0, color.lighter(112))
                    grad.setColorAt(1, color.darker(118))
                    painter.setBrush(QBrush(grad))
                else:
                    painter.setBrush(QBrush(color))

            painter.drawRect(geom)

            # ── Directory header strip ─────────────────────────────────
            if is_dir and h > 18:
                header_bg = color.darker(130)
                header_bg.setAlpha(220)
                painter.fillRect(QRectF(x + 1, y + 1, w - 2, 17), header_bg)

            # ── Text label ────────────────────────────────────────────
            if w > 38 and h > 16:
                lum = color.lightness()
                painter.setPen(QColor("#ffffff") if lum < 155 else QColor("#111111"))
                text = fm.elidedText(
                    box["name"], Qt.TextElideMode.ElideRight, int(w) - 8
                )
                if is_dir:
                    painter.drawText(
                        QRectF(x + 5, y + 2, w - 10, 15),
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        text,
                    )
                elif h > 28:
                    painter.drawText(
                        QRectF(x + 4, y + 4, w - 8, h - 8),
                        Qt.AlignmentFlag.AlignCenter,
                        text,
                    )

        # Draw path header on top of content
        current_path = self._nav_stack[-1] if self._nav_stack else []
        self._draw_header_on(painter, current_path)
        painter.end()

    def _draw_header(self, painter: QPainter, path: list[str]) -> None:
        """Draw header strip directly onto the widget painter (empty state)."""
        painter.fillRect(QRectF(0, 0, self.width(), _HEADER_H), _BG_HEADER)
        painter.fillRect(QRectF(0, _HEADER_H - 1, self.width(), 1), _BORDER)

    def _draw_header_on(self, painter: QPainter, path: list[str]) -> None:
        """Draw path header onto an already-active painter."""
        w = painter.device().width() if painter.device() else self.width()

        painter.fillRect(QRectF(0, 0, w, _HEADER_H), _BG_HEADER)
        painter.fillRect(QRectF(0, _HEADER_H - 1, w, 1), _BORDER)

        painter.setFont(self._path_font)
        fm = QFontMetrics(self._path_font)

        # Build path string
        if self._root:
            root_name = self._root.name.rstrip("\\")
            if path:
                full = root_name + "\\" + "\\".join(path)
            else:
                full = root_name + "\\"
        else:
            full = "\\"

        # Truncate from left if too wide
        max_w = w - 60
        display = fm.elidedText(full, Qt.TextElideMode.ElideLeft, max_w)

        painter.setPen(_TEXT_MUTED)
        painter.drawText(
            QRectF(14, 0, max_w, _HEADER_H),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            display,
        )

        # Size of current node
        if self._current_node:
            size_str = format_bytes(self._current_node.total_size)
            painter.setPen(_ACCENT)
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(
                QRectF(0, 0, w - 12, _HEADER_H),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                size_str,
            )

    def _draw_empty_state(self, painter: QPainter) -> None:
        center_y = _HEADER_H + (self.height() - _HEADER_H) // 2

        painter.setFont(QFont("Segoe UI Emoji", 40))
        painter.setPen(QColor("#252725"))
        icon_rect = QRect(0, center_y - 70, self.width(), 60)
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, "💿")

        painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Normal))
        painter.setPen(QColor("#303230"))
        msg_rect = QRect(0, center_y - 8, self.width(), 28)
        painter.drawText(msg_rect, Qt.AlignmentFlag.AlignCenter, "Selecciona una unidad y haz clic en Analizar")

    # ------------------------------------------------------------------ #
    # Interaction
    # ------------------------------------------------------------------ #

    def _get_box_at(self, pos: QPointF) -> Optional[dict]:
        # Skip header zone
        if pos.y() < _HEADER_H:
            return None
        for box in reversed(self._boxes):
            x, y, w, h = box["rect"]
            if x <= pos.x() <= x + w and y <= pos.y() <= y + h:
                return box
        return None

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        box = self._get_box_at(event.position())

        if box != self._hovered_box:
            self._hovered_box = box
            self.update()

            if box:
                is_dir = box.get("is_dir", False)
                # Change cursor to pointer for dirs (clickable)
                self.setCursor(
                    Qt.CursorShape.PointingHandCursor if is_dir
                    else Qt.CursorShape.ArrowCursor
                )
                size_str = format_bytes(box["size"])
                kind = "Carpeta" if is_dir else "Archivo"
                action = " — clic para abrir" if is_dir else ""
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    f"<b>{box['name']}</b><br>{kind} · {size_str}{action}",
                    self,
                )
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
                QToolTip.hideText()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        box = self._hovered_box
        if not box:
            return

        if event.button() == Qt.MouseButton.RightButton:
            self._handle_context_menu(event.globalPosition().toPoint(), box)
            return

        if event.button() != Qt.MouseButton.LeftButton:
            return

        path_parts = box.get("path_parts")
        if path_parts is None:
            return

        if box.get("is_dir"):
            self.navigate_to(path_parts)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        # Double-click also navigates (belt & suspenders)
        self.mousePressEvent(event)

    def _handle_context_menu(self, pos, box: dict) -> None:
        import os
        import subprocess
        import send2trash
        from PyQt6.QtWidgets import QMenu, QApplication, QMessageBox

        path_parts = box.get("path_parts")
        if path_parts is None or not self._root:
            return

        full_path = os.path.join(self._root.name, *path_parts)
        is_dir    = box.get("is_dir", False)

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1b1b;
                color: #e2e2e2;
                border: 1px solid #2e2f2f;
                border-radius: 8px;
                padding: 4px;
                font-size: 13px;
            }
            QMenu::item {
                padding: 7px 24px 7px 16px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background-color: rgba(255, 96, 68, 0.15);
                color: #ff7557;
            }
            QMenu::separator {
                height: 1px;
                background: #252626;
                margin: 4px 8px;
            }
        """)

        open_act = menu.addAction("🔍  Abrir en el Explorador")
        copy_act = menu.addAction("📋  Copiar Ruta")
        menu.addSeparator()
        del_act  = menu.addAction("🗑  Eliminar (Papelera de Reciclaje)")

        action = menu.exec(pos)
        if not action:
            return

        if action == open_act:
            if is_dir:
                subprocess.Popen(["explorer", full_path])
            else:
                subprocess.Popen(["explorer", "/select,", full_path])
        elif action == copy_act:
            QApplication.clipboard().setText(full_path)
        elif action == del_act:
            reply = QMessageBox.question(
                self,
                "Confirmar eliminación",
                f"¿Mover a la Papelera de Reciclaje?\n\n{full_path}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    send2trash.send2trash(full_path)
                    QMessageBox.information(
                        self,
                        "Eliminado",
                        "Movido a la Papelera exitosamente.\n"
                        "(Actualiza el análisis para ver los cambios reflejados)",
                    )
                except Exception as exc:
                    QMessageBox.critical(self, "Error", f"No se pudo eliminar:\n{exc}")
