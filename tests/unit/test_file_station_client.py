"""Unit tests for FileStationClient's browsing/URL-building logic.

These tests never touch the network: FileStationClient.__init__ (which would
log in to a real DSM) is bypassed via object.__new__, and a fake ``_fs``
object stands in for ``synology_api.filestation.FileStation``. This matches
docs/design.md 7.1 ("mock HTTP responses / dependencies, no real network").
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from synology_api.exceptions import FileStationError

from ds_video.api.exceptions import ApiError
from ds_video.api.file_station import FileStationClient


class FakeFileStation:
    def __init__(self, share_response=None, file_list_response=None):
        self._share_response = share_response
        self._file_list_response = file_list_response
        self.base_url = "http://nas:5000/webapi/"
        self.file_station_list = {
            "SYNO.FileStation.Download": {"path": "entry.cgi", "minVersion": 1, "maxVersion": 2},
        }
        self.session = SimpleNamespace(sid="SID123", syno_token="TOKEN456")

    def get_list_share(self):
        return self._share_response

    def get_file_list(self, path):
        return self._file_list_response


def make_client(fake_fs: FakeFileStation) -> FileStationClient:
    client = object.__new__(FileStationClient)
    client._fs = fake_fs
    return client


def test_list_shares_parses_response() -> None:
    fake = FakeFileStation(share_response={"data": {"shares": [{"name": "video", "path": "/video"}]}})
    client = make_client(fake)

    shares = client.list_shares()

    assert len(shares) == 1
    assert shares[0].path == "/video"
    assert shares[0].name == "video"
    assert shares[0].is_folder is True


def test_list_folder_distinguishes_folders_and_files() -> None:
    fake = FakeFileStation(
        file_list_response={
            "data": {
                "files": [
                    {"name": "电影", "path": "/video/电影", "isdir": True},
                    {"name": "movie.mkv", "path": "/video/movie.mkv", "isdir": False},
                ]
            }
        }
    )
    client = make_client(fake)

    entries = client.list_folder("/video")

    assert entries[0].is_folder is True
    assert entries[1].is_folder is False
    assert entries[1].path == "/video/movie.mkv"


def test_list_shares_wraps_file_station_error() -> None:
    class RaisingFakeFileStation(FakeFileStation):
        def get_list_share(self):
            raise FileStationError(error_code=408)

    client = make_client(RaisingFakeFileStation())
    with pytest.raises(ApiError):
        client.list_shares()


def test_list_folder_wraps_file_station_error() -> None:
    class RaisingFakeFileStation(FakeFileStation):
        def get_file_list(self, path):
            raise FileStationError(error_code=408)

    client = make_client(RaisingFakeFileStation())
    with pytest.raises(ApiError):
        client.list_folder("/video")


def test_get_stream_url_includes_sid_and_token() -> None:
    fake = FakeFileStation()
    client = make_client(fake)

    url = client.get_stream_url("/video/电影/movie.mp4")

    assert url.startswith("http://nas:5000/webapi/entry.cgi?")
    assert "api=SYNO.FileStation.Download" in url
    assert "method=download" in url
    assert "mode=open" in url
    assert "_sid=SID123" in url
    assert "SynoToken=TOKEN456" in url
    # Path must be URL-encoded (spaces/unicode), not embedded raw.
    assert "movie.mp4" in url


def test_get_stream_url_raises_when_download_api_unavailable() -> None:
    fake = FakeFileStation()
    fake.file_station_list = {}
    client = make_client(fake)

    with pytest.raises(ApiError):
        client.get_stream_url("/video/movie.mp4")
