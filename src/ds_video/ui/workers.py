"""Shared QThread workers for blocking DSM calls.

Both the initial login (LoginWindow) and reconnect-after-disconnect
(MainWindow, e.g. after the DSM device reboots) need to run
``FileStationClient(...)`` off the Qt UI thread, so this is factored out
into one place instead of duplicated.
"""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from ds_video.api import ApiError, AuthError, FileStationClient, SessionExpiredError
from ds_video.config import DsmConnectionSettings


class LoginWorker(QThread):
    """Runs the (blocking) DSM login call off the Qt UI thread."""

    succeeded = pyqtSignal(object)  # FileStationClient
    failed = pyqtSignal(str)

    def __init__(self, settings: DsmConnectionSettings) -> None:
        super().__init__()
        self._settings = settings

    def run(self) -> None:
        try:
            client = FileStationClient(
                ip_address=self._settings.host,
                port=self._settings.port,
                username=self._settings.username,
                password=self._settings.password,
                secure=self._settings.secure,
            )
        except AuthError as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - never let an exception
            # escape a QThread: that would abort the whole PyQt process
            # instead of just failing this login/reconnect attempt.
            self.failed.emit(f"未预期的错误：{exc}")
            return
        self.succeeded.emit(client)


class HeartbeatWorker(QThread):
    """Runs a cheap, periodic liveness check against DSM off the UI thread.

    Used by ``MainWindow`` to notice a dropped/expired session (e.g. the
    DSM device rebooting) on its own, instead of waiting for the user to
    click around and hit a load error first -- see ``MainWindow._run_heartbeat``.
    """

    ok = pyqtSignal()
    failed = pyqtSignal(object)  # the ApiError/SessionExpiredError instance

    def __init__(self, client: FileStationClient) -> None:
        super().__init__()
        self._client = client

    def run(self) -> None:
        try:
            self._client.ping()
        except (ApiError, SessionExpiredError) as exc:
            self.failed.emit(exc)
            return
        except Exception as exc:  # noqa: BLE001 - never let an exception
            # escape a QThread: that would abort the whole PyQt process
            # instead of just failing this one heartbeat tick.
            self.failed.emit(ApiError(f"未预期的错误：{exc}"))
            return
        self.ok.emit()
