"""Application entry point: wires LoginWindow -> MainWindow -> VLC playback together."""

from __future__ import annotations

import logging
import sys
import traceback

from PyQt6.QtWidgets import QApplication, QMessageBox

from ds_video.api import FileStationClient
from ds_video.config import DsmConnectionSettings
from ds_video.logging_setup import configure_logging
from ds_video.ui.login_window import LoginWindow
from ds_video.ui.main_window import MainWindow
from ds_video.ui.theme import apply_theme
from ds_video.ui.vlc_launcher import VlcLauncher

_logger = logging.getLogger("ds_video.ui.app")


def _install_global_excepthook() -> None:
    """Last line of defense: any exception that escapes a Qt slot would
    otherwise abort the whole process instead of just failing one action.
    Log it and show a dialog instead of crashing.
    """

    def _handle(exc_type, exc_value, exc_tb) -> None:
        _logger.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
        message = "".join(traceback.format_exception_only(exc_type, exc_value)).strip()
        app = QApplication.instance()
        if app is not None:
            QMessageBox.critical(None, "发生错误", f"出现未预期的错误，已记录到日志：\n{message}")

    sys.excepthook = _handle


class AppController:
    """Owns the window instances so they aren't garbage-collected between steps."""

    def __init__(self) -> None:
        self.login_window: LoginWindow | None = None
        self.main_window: MainWindow | None = None

    def start(self) -> None:
        self.login_window = LoginWindow()
        self.login_window.login_succeeded.connect(self._on_login_succeeded)
        self.login_window.show()

    def _on_login_succeeded(self, client: FileStationClient, _settings: DsmConnectionSettings) -> None:
        self.main_window = MainWindow(client)
        self.main_window.file_activated.connect(lambda path, name: self._on_file_activated(client, path, name))
        self.main_window.show()
        if self.login_window is not None:
            self.login_window.close()

    def _on_file_activated(self, client: FileStationClient, path: str, _name: str) -> None:
        # No intermediate window/dialog for the success path: double-clicking
        # a video should just open it in VLC directly. Errors (couldn't get
        # the stream URL, VLC missing, VLC failed to start) still surface via
        # a message box from VlcLauncher itself.
        VlcLauncher(client, parent=self.main_window).play_file(path)


def main() -> int:
    configure_logging()
    app = QApplication(sys.argv)
    # Match this app's Wayland app_id / X11 WM_CLASS to the installed
    # ds-video.desktop entry, so GNOME (and other desktops) resolve the
    # taskbar/dash icon from that .desktop file's Icon= line instead of
    # falling back to a generic Python icon. See resources/ds-video.desktop.
    app.setDesktopFileName("ds-video")
    app.setApplicationName("DS Video")
    apply_theme(app)
    _install_global_excepthook()
    controller = AppController()
    controller.start()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
