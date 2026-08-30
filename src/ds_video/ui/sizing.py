"""Small helper to give top-level windows a sensible default size instead of
Qt's tiny auto-sized-to-widgets default (see AGENTS.md / docs/design.md UI
notes)."""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication, QWidget


def apply_preferred_size(
    widget: QWidget,
    preferred_width: int,
    preferred_height: int,
) -> None:
    """Resize ``widget`` to a fixed preferred size, clamped down to the
    primary screen's available size on smaller displays so the window never
    opens larger than the screen it's shown on, and centered on that screen
    rather than left at Qt's default top-left placement.
    """
    screen = QApplication.primaryScreen()
    if screen is None:
        widget.resize(preferred_width, preferred_height)
        return
    geometry = screen.availableGeometry()
    width = min(preferred_width, geometry.width())
    height = min(preferred_height, geometry.height())
    widget.resize(width, height)
    x = geometry.x() + (geometry.width() - width) // 2
    y = geometry.y() + (geometry.height() - height) // 2
    widget.move(x, y)
