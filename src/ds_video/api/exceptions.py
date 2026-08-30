"""Custom exceptions for the ds_video API layer.

All errors raised while talking to DSM / Video Station are normalized to one
of these types so the UI layer only needs to handle a small, stable set of
exceptions instead of every possible ``synology_api`` exception class.
"""

from __future__ import annotations


class DsVideoError(Exception):
    """Base class for all ds_video errors."""


class AuthError(DsVideoError):
    """Raised when login to DSM fails (bad credentials, unreachable host, ...)."""


class SessionExpiredError(DsVideoError):
    """Raised when a previously valid DSM session has expired or was revoked."""


class ApiError(DsVideoError):
    """Raised when a Video Station API call returns an error response.

    Attributes
    ----------
    api_name:
        The ``SYNO.VideoStation.*`` API name that failed.
    error_code:
        The raw error code returned by DSM, when available.
    """

    def __init__(self, message: str, api_name: str | None = None, error_code: int | None = None) -> None:
        super().__init__(message)
        self.api_name = api_name
        self.error_code = error_code
