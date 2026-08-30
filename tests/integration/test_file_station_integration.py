"""Integration tests against a real DSM 7.2 File Station instance.

Per docs/design.md section 7.2, these require a real device and are skipped
unless connection details are provided via environment variables:

    DS_VIDEO_TEST_HOST, DS_VIDEO_TEST_PORT,
    DS_VIDEO_TEST_USERNAME, DS_VIDEO_TEST_PASSWORD

Run explicitly with, e.g.:

    DS_VIDEO_TEST_HOST=192.168.1.10 DS_VIDEO_TEST_PORT=5000 \\
    DS_VIDEO_TEST_USERNAME=alice DS_VIDEO_TEST_PASSWORD=secret \\
    pytest -m integration tests/integration
"""

from __future__ import annotations

import os

import pytest
import requests

from ds_video.api import FileStationClient

pytestmark = pytest.mark.integration

_REQUIRED_ENV = [
    "DS_VIDEO_TEST_HOST",
    "DS_VIDEO_TEST_PORT",
    "DS_VIDEO_TEST_USERNAME",
    "DS_VIDEO_TEST_PASSWORD",
]

_missing = [name for name in _REQUIRED_ENV if not os.environ.get(name)]


@pytest.mark.skipif(_missing, reason=f"Missing env vars for real-device test: {_missing}")
class TestFileStationIntegration:
    @pytest.fixture()
    def client(self):
        client = FileStationClient(
            ip_address=os.environ["DS_VIDEO_TEST_HOST"],
            port=os.environ["DS_VIDEO_TEST_PORT"],
            username=os.environ["DS_VIDEO_TEST_USERNAME"],
            password=os.environ["DS_VIDEO_TEST_PASSWORD"],
        )
        yield client
        client.logout()

    def test_login_and_list_shares(self, client: FileStationClient) -> None:
        shares = client.list_shares()
        assert isinstance(shares, list)

    def test_stream_url_is_playable_and_supports_range(self, client: FileStationClient) -> None:
        """Find any video-looking file and confirm the stream URL is fetchable
        with a byte-range request (what VLC relies on for seeking)."""
        shares = client.list_shares()
        video_exts = (".mp4", ".mkv", ".avi", ".mov", ".ts", ".m4v")

        def find_video(path: str, depth: int = 0):
            if depth > 4:
                return None
            for entry in client.list_folder(path):
                if entry.is_folder:
                    found = find_video(entry.path, depth + 1)
                    if found:
                        return found
                elif entry.name.lower().endswith(video_exts):
                    return entry.path
            return None

        video_path = None
        for share in shares:
            video_path = find_video(share.path)
            if video_path:
                break

        if video_path is None:
            pytest.skip("No video files found on this DSM to test streaming against")

        url = client.get_stream_url(video_path)
        response = requests.get(url, headers={"Range": "bytes=0-1023"}, timeout=10)
        assert response.status_code == 206
        assert response.headers.get("Accept-Ranges") == "bytes"
        assert len(response.content) == 1024
