"""Client for browsing and streaming videos via DSM's built-in File Station.

Unlike Video Station (which turned out to not be installed on the target DSM,
see docs/design.md 2026-08-29 change note), File Station is always available
on DSM and is fully supported by ``synology-api`` out of the box
(``synology_api.filestation.FileStation``), so this module is a thin wrapper
around it rather than a from-scratch API client.

Confirmed against a real DSM 7.2 device (docs/design.md section 2.2):
- Browsing: ``SYNO.FileStation.List`` (``list_share`` for shared folders,
  ``list`` for folder contents).
- Streaming: a self-contained URL for ``SYNO.FileStation.Download`` with both
  ``_sid`` and ``SynoToken`` as query parameters (no custom HTTP header
  needed), which DSM serves with ``Accept-Ranges: bytes`` / 206 responses -
  i.e. VLC can play and seek it directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from synology_api import filestation
from synology_api.exceptions import (
    FileStationError,
    HTTPError,
    LoginError,
    SynoConnectionError,
)

from ds_video.api.exceptions import ApiError, AuthError


@dataclass
class FileEntry:
    """A single entry (folder or video file) returned when browsing."""

    path: str
    name: str
    is_folder: bool
    raw: dict[str, Any]


class FileStationClient:
    """Browse shared folders/files and build streaming URLs via File Station."""

    def __init__(
        self,
        ip_address: str,
        port: str,
        username: str,
        password: str,
        secure: bool = False,
        cert_verify: bool = False,
        dsm_version: int = 7,
        debug: bool = False,
    ) -> None:
        try:
            self._fs = filestation.FileStation(
                ip_address,
                port,
                username,
                password,
                secure,
                cert_verify,
                dsm_version,
                debug,
            )
        except (LoginError, SynoConnectionError, HTTPError) as exc:
            raise AuthError(f"Failed to log in to DSM at {ip_address}:{port}: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - never let raw network/SSL
            # errors escape: on a background QThread these would otherwise
            # abort the whole PyQt process instead of showing an error dialog.
            raise AuthError(f"Failed to log in to DSM at {ip_address}:{port}: {exc}") from exc

    # -- browsing --------------------------------------------------------

    def list_shares(self) -> list[FileEntry]:
        """Return the top-level shared folders (tree root nodes)."""
        try:
            data = self._fs.get_list_share()
        except (FileStationError, SynoConnectionError, HTTPError) as exc:
            raise ApiError(f"Failed to list shared folders: {exc}") from exc
        shares = data.get("data", {}).get("shares", [])
        return [
            FileEntry(path=s["path"], name=s.get("name", s["path"]), is_folder=True, raw=s)
            for s in shares
        ]

    def list_folder(self, path: str) -> list[FileEntry]:
        """List the folders and files directly under ``path``."""
        try:
            data = self._fs.get_file_list(path)
        except (FileStationError, SynoConnectionError, HTTPError) as exc:
            raise ApiError(f"Failed to list folder '{path}': {exc}") from exc
        files = data.get("data", {}).get("files", [])
        return [
            FileEntry(path=f["path"], name=f.get("name", f["path"]), is_folder=bool(f.get("isdir")), raw=f)
            for f in files
        ]

    # -- streaming ---------------------------------------------------------

    def get_stream_url(self, path: str) -> str:
        """Build a self-contained, playable HTTP(S) URL for a video file.

        The URL carries ``_sid``/``SynoToken`` as query parameters (confirmed
        working against a real DSM 7.2 device) so VLC can open/seek it
        directly without any custom HTTP headers.
        """
        api_name = "SYNO.FileStation.Download"
        try:
            info = self._fs.file_station_list[api_name]
        except KeyError as exc:
            raise ApiError(f"API '{api_name}' is not available on this DSM.") from exc

        session = self._fs.session
        return (
            f"{self._fs.base_url}{info['path']}"
            f"?api={api_name}&version={info['maxVersion']}&method=download"
            f"&path={quote(path)}&mode=open"
            f"&_sid={session.sid}&SynoToken={session.syno_token}"
        )

    def logout(self) -> None:
        """Log out and release the underlying DSM session."""
        self._fs.logout()
