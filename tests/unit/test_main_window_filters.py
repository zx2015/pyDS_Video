"""Unit test for the pure video-extension filter used by MainWindow's file
list, so images/subtitles/docs never show up as "playable" entries."""

from __future__ import annotations

import pytest

from ds_video.ui.main_window import _is_video_file


@pytest.mark.parametrize(
    "name,expected",
    [
        ("movie.mp4", True),
        ("movie.MKV", True),
        ("电影.avi", True),
        ("poster.jpg", False),
        ("subtitle.srt", False),
        ("readme.txt", False),
        ("no_extension", False),
        ("movie.mp4.part", False),  # in-progress download, not a real video
    ],
)
def test_is_video_file(name: str, expected: bool) -> None:
    assert _is_video_file(name) is expected
