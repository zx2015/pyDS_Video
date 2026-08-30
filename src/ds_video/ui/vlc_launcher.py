"""VLC launcher: plays a video by spawning the system VLC application,
with no intermediate Qt window/dialog for normal playback.

Earlier revisions showed a small "PlayerWindow" with a status label and a
stop button. Per user feedback, double-clicking a video should just open
VLC directly with no extra dialog in the way. This module only pops up a
``QMessageBox`` for genuine failures (couldn't get the stream URL, VLC not
installed, VLC failed to start) — never for the success path.

Earlier revisions also tried to embed VLC's video output directly into a Qt
widget via python-vlc (``set_xwindow``/``set_nsobject``). On this project's
target Linux desktops that turned out to be unreliable: under a native
Wayland session without the ``xcb`` Qt platform plugin (e.g. missing the
``libxcb-cursor0`` system package), handing libvlc a non-X11 window ID hung
the whole application, and VLC 3.x's own Wayland video-output modules
(``wl_shell``/``wl_shm``) don't work with GNOME/mutter's ``xdg_shell``
either. Spawning the system ``vlc`` binary as an independent process was
confirmed (real-device testing) to play back reliably and can never freeze
this app, at the cost of playback controls living in VLC's own window
instead of ours. See docs/design.md's 2026-08-29 change notes.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys

from PyQt6.QtWidgets import QMessageBox, QWidget

from ds_video.api import ApiError, FileStationClient

_logger = logging.getLogger("ds_video.ui.vlc_launcher")

_INSTALL_HINTS = {
    "darwin": "brew install --cask vlc（或从 https://www.videolan.org/vlc/ 下载安装）",
    "linux": "sudo apt install vlc（或对应发行版的包管理器，如 dnf/pacman）",
}


def _find_vlc_executable() -> str | None:
    """Locate the system VLC executable, checking common install paths too."""
    found = shutil.which("vlc")
    if found:
        return found
    if sys.platform == "darwin":
        mac_path = "/Applications/VLC.app/Contents/MacOS/VLC"
        # shutil.which() only searches $PATH entries; a full path like this
        # must be checked directly for existence + executability instead.
        if os.path.isfile(mac_path) and os.access(mac_path, os.X_OK):
            return mac_path
    return None


class VlcLauncher:
    """Launches an independent VLC process for a video.

    Not a QWidget/window: playing a video shows no dialog of its own, only
    an error message box if something actually goes wrong. Each call spawns
    its own independent VLC process (matching the app's original launch
    behavior), so multiple videos can be opened without one stopping
    another; VLC's own windows are the user's playback controls.
    """

    def __init__(self, client: FileStationClient, parent: QWidget | None = None) -> None:
        self._client = client
        self._parent = parent

    def play_file(self, path: str) -> None:
        try:
            url = self._client.get_stream_url(path)
        except ApiError as exc:
            QMessageBox.critical(self._parent, "播放失败", f"无法获取播放地址：{exc}")
            return

        vlc_path = _find_vlc_executable()
        if vlc_path is None:
            hint = _INSTALL_HINTS.get(sys.platform, "请从 https://www.videolan.org/vlc/ 下载安装 VLC")
            message = f"未检测到系统安装的 VLC，无法播放视频。\n请先安装 VLC：{hint}\n安装后重新打开该视频即可。"
            QMessageBox.warning(self._parent, "未安装 VLC", message)
            return

        try:
            subprocess.Popen([vlc_path, url])
        except OSError as exc:
            _logger.error("Failed to launch VLC", exc_info=exc)
            QMessageBox.critical(self._parent, "播放失败", f"启动 VLC 失败：{exc}")
