"""Unit tests for VlcLauncher's pure helper logic (no Qt event loop needed:
these only touch ``_find_vlc_executable``, which has no PyQt dependency)."""

from __future__ import annotations

import sys

from ds_video.ui.vlc_launcher import _find_vlc_executable


def test_find_vlc_executable_uses_path_lookup(monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/vlc" if name == "vlc" else None)

    assert _find_vlc_executable() == "/usr/bin/vlc"


def test_find_vlc_executable_returns_none_when_not_installed(monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setattr(sys, "platform", "linux")

    assert _find_vlc_executable() is None


def test_find_vlc_executable_checks_mac_app_bundle_path(monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setattr(sys, "platform", "darwin")
    # Prove the code checks the literal filesystem path via os.path.isfile,
    # not shutil.which(full_path) (which never matches a full path).
    monkeypatch.setattr(
        "ds_video.ui.vlc_launcher.os.path.isfile",
        lambda p: p == "/Applications/VLC.app/Contents/MacOS/VLC",
    )
    monkeypatch.setattr(
        "ds_video.ui.vlc_launcher.os.access",
        lambda p, mode: p == "/Applications/VLC.app/Contents/MacOS/VLC",
    )

    assert _find_vlc_executable() == "/Applications/VLC.app/Contents/MacOS/VLC"
