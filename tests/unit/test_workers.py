"""Unit tests for the QThread workers in ds_video.ui.workers.

These call ``.run()`` directly instead of ``.start()`` so the worker body
executes synchronously on the test thread -- no real threading or Qt event
loop is needed to observe which signal fires, since same-thread signal/slot
connections are invoked directly (not queued).
"""

from __future__ import annotations

from ds_video.api import ApiError, AuthError, SessionExpiredError
from ds_video.config import DsmConnectionSettings
from ds_video.ui.workers import HeartbeatWorker, LoginWorker


def test_login_worker_emits_succeeded_with_client(monkeypatch) -> None:
    fake_client = object()
    monkeypatch.setattr(
        "ds_video.ui.workers.FileStationClient",
        lambda **kwargs: fake_client,
    )
    settings = DsmConnectionSettings(host="h", port="5000", username="u", password="p")
    worker = LoginWorker(settings)

    results: dict[str, object] = {}
    worker.succeeded.connect(lambda client: results.setdefault("client", client))
    worker.failed.connect(lambda message: results.setdefault("failed", message))
    worker.run()

    assert results.get("client") is fake_client
    assert "failed" not in results


def test_login_worker_emits_failed_on_auth_error(monkeypatch) -> None:
    def raise_auth_error(**kwargs):
        raise AuthError("bad credentials")

    monkeypatch.setattr("ds_video.ui.workers.FileStationClient", raise_auth_error)
    settings = DsmConnectionSettings(host="h", port="5000", username="u", password="p")
    worker = LoginWorker(settings)

    results: dict[str, object] = {}
    worker.succeeded.connect(lambda client: results.setdefault("client", client))
    worker.failed.connect(lambda message: results.setdefault("failed", message))
    worker.run()

    assert "client" not in results
    assert "bad credentials" in results["failed"]


def test_login_worker_emits_failed_on_unexpected_exception(monkeypatch) -> None:
    def raise_unexpected(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("ds_video.ui.workers.FileStationClient", raise_unexpected)
    settings = DsmConnectionSettings(host="h", port="5000", username="u", password="p")
    worker = LoginWorker(settings)

    results: dict[str, object] = {}
    worker.failed.connect(lambda message: results.setdefault("failed", message))
    worker.run()

    assert "boom" in results["failed"]


def test_heartbeat_worker_emits_ok_when_ping_succeeds() -> None:
    class FakeClient:
        def ping(self) -> None:
            return None

    worker = HeartbeatWorker(FakeClient())
    results: dict[str, object] = {}
    worker.ok.connect(lambda: results.setdefault("ok", True))
    worker.failed.connect(lambda exc: results.setdefault("failed", exc))
    worker.run()

    assert results.get("ok") is True
    assert "failed" not in results


def test_heartbeat_worker_emits_failed_on_session_expired() -> None:
    class FakeClient:
        def ping(self) -> None:
            raise SessionExpiredError("session expired")

    worker = HeartbeatWorker(FakeClient())
    results: dict[str, object] = {}
    worker.ok.connect(lambda: results.setdefault("ok", True))
    worker.failed.connect(lambda exc: results.setdefault("failed", exc))
    worker.run()

    assert "ok" not in results
    assert isinstance(results["failed"], SessionExpiredError)


def test_heartbeat_worker_wraps_unexpected_exception_as_api_error() -> None:
    class FakeClient:
        def ping(self) -> None:
            raise RuntimeError("network gone")

    worker = HeartbeatWorker(FakeClient())
    results: dict[str, object] = {}
    worker.failed.connect(lambda exc: results.setdefault("failed", exc))
    worker.run()

    assert isinstance(results["failed"], ApiError)
    assert "network gone" in str(results["failed"])
