"""Shared visual theme: one restrained dark palette and QSS stylesheet applied
app-wide, so every window shares consistent typography, color, spacing, and
component states instead of PyQt6's unstyled defaults (Operate-mode UI, per
docs/design.md — the tool should disappear into the task, not call attention
to itself).
"""

from __future__ import annotations

from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

# -- palette --------------------------------------------------------------
# A single neutral dark surface stack plus one accent, per the Operate-mode
# floor: restrained color, accent reserved for primary actions/selection.
BACKGROUND = "#1a1c22"
SURFACE = "#20222a"
SURFACE_RAISED = "#282b34"
BORDER = "#383c47"
BORDER_STRONG = "#474c59"
TEXT_PRIMARY = "#e9ebf1"
TEXT_SECONDARY = "#9aa0ad"
TEXT_MUTED = "#6b7280"
ACCENT = "#5b8cff"
ACCENT_HOVER = "#7099ff"
ACCENT_PRESSED = "#4874e0"
ACCENT_MUTED = "#33405e"
DANGER = "#e8635f"
DANGER_HOVER = "#ef7a76"
DANGER_PRESSED = "#d1524e"
SUCCESS = "#3ecf8e"

_FONT_FAMILY = "Noto Sans CJK SC, PingFang SC, Microsoft YaHei, Segoe UI, sans-serif"

STYLESHEET = f"""
* {{
    font-family: {_FONT_FAMILY};
    outline: none;
}}

QWidget {{
    background-color: {BACKGROUND};
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}

QMainWindow, QDialog {{
    background-color: {BACKGROUND};
}}

QLabel[variant="title"] {{
    font-size: 20px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}

QLabel[variant="subtitle"] {{
    font-size: 13px;
    color: {TEXT_SECONDARY};
}}

QLabel[variant="section"] {{
    font-size: 11px;
    font-weight: 600;
    color: {TEXT_MUTED};
    letter-spacing: 1px;
}}

QLabel[variant="hint"] {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}

QLabel[variant="status-ok"] {{
    color: {SUCCESS};
    font-weight: 600;
}}

QLabel[variant="status-error"] {{
    color: {DANGER};
    font-weight: 600;
}}

QFrame[variant="card"] {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

QLineEdit {{
    background-color: {SURFACE_RAISED};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 7px 10px;
    color: {TEXT_PRIMARY};
    selection-background-color: {ACCENT};
}}

QLineEdit:focus {{
    border: 1px solid {ACCENT};
}}

QLineEdit:disabled {{
    color: {TEXT_MUTED};
    background-color: {SURFACE};
}}

QCheckBox {{
    color: {TEXT_SECONDARY};
    spacing: 8px;
    padding: 2px 0;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {BORDER_STRONG};
    background-color: {SURFACE_RAISED};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border: 1px solid {ACCENT};
}}

QPushButton {{
    background-color: {SURFACE_RAISED};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 8px 16px;
    color: {TEXT_PRIMARY};
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {BORDER};
}}

QPushButton:pressed {{
    background-color: {BORDER_STRONG};
}}

QPushButton:disabled {{
    color: {TEXT_MUTED};
    border-color: {BORDER};
    background-color: {SURFACE};
}}

QPushButton[variant="primary"] {{
    background-color: {ACCENT};
    border: 1px solid {ACCENT};
    color: #ffffff;
}}

QPushButton[variant="primary"]:hover {{
    background-color: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}

QPushButton[variant="primary"]:pressed {{
    background-color: {ACCENT_PRESSED};
    border-color: {ACCENT_PRESSED};
}}

QPushButton[variant="primary"]:disabled {{
    background-color: {ACCENT_MUTED};
    border-color: {ACCENT_MUTED};
    color: #a9b6d6;
}}

QPushButton[variant="danger"] {{
    background-color: transparent;
    border: 1px solid {DANGER};
    color: {DANGER};
}}

QPushButton[variant="danger"]:hover {{
    background-color: {DANGER};
    color: #ffffff;
}}

QPushButton[variant="danger"]:pressed {{
    background-color: {DANGER_PRESSED};
    color: #ffffff;
}}

QToolBar {{
    background-color: {SURFACE};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px 10px;
    spacing: 8px;
}}

QStatusBar {{
    background-color: {SURFACE};
    border-top: 1px solid {BORDER};
    color: {TEXT_SECONDARY};
}}

QTreeWidget, QListWidget {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px;
    alternate-background-color: transparent;
}}

QTreeWidget::item, QListWidget::item {{
    padding: 6px 8px;
    border-radius: 5px;
    color: {TEXT_PRIMARY};
}}

QTreeWidget::item:hover, QListWidget::item:hover {{
    background-color: {SURFACE_RAISED};
}}

QTreeWidget::item:selected, QListWidget::item:selected {{
    background-color: {ACCENT_MUTED};
    color: {TEXT_PRIMARY};
}}

QHeaderView::section {{
    background-color: {SURFACE};
    color: {TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px 8px;
    font-weight: 600;
}}

QSplitter::handle {{
    background-color: {BACKGROUND};
    width: 10px;
}}

QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {ACCENT};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}

QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {BORDER_STRONG};
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {TEXT_MUTED};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QToolTip {{
    background-color: {SURFACE_RAISED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_STRONG};
    padding: 4px 8px;
    border-radius: 4px;
}}
"""


def apply_theme(app: QApplication) -> None:
    """Install the app-wide font and QSS stylesheet."""
    app.setStyle("Fusion")
    font = QFont()
    font.setPointSize(10)
    app.setFont(font)
    app.setStyleSheet(STYLESHEET)
    app.setWindowIcon(make_app_icon())


def make_app_icon(size: int = 128) -> QIcon:
    """Draw a simple rounded-square play-button mark, so the app has a
    distinct icon/logo without requiring an external asset file."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    background = QPainterPath()
    margin = size * 0.06
    background.addRoundedRect(margin, margin, size - 2 * margin, size - 2 * margin, size * 0.22, size * 0.22)
    painter.fillPath(background, QColor(ACCENT))

    triangle = QPainterPath()
    cx, cy = size / 2, size / 2
    t = size * 0.22
    triangle.moveTo(cx - t * 0.6, cy - t)
    triangle.lineTo(cx - t * 0.6, cy + t)
    triangle.lineTo(cx + t * 0.9, cy)
    triangle.closeSubpath()
    painter.fillPath(triangle, QColor("#ffffff"))

    painter.end()
    return QIcon(pixmap)
