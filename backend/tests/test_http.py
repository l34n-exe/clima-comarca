import pytest  # pyright: ignore[reportMissingImports]
import requests  # pyright: ignore[reportMissingImports]

from app.core.exceptions import WeatherError
from app.infrastructure import http


class FakeResponse:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        return self._payload


def test_get_retries_on_5xx(app, monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None, headers=None):
        calls.append(1)
        return FakeResponse(500) if len(calls) < 3 else FakeResponse(200, {"ok": True})

    monkeypatch.setattr(http.requests, "get", fake_get)
    monkeypatch.setattr(http.time, "sleep", lambda seconds: None)
    with app.app_context():
        assert http.get("http://proveedor", params={}).json() == {"ok": True}
    assert len(calls) == 3


def test_get_does_not_retry_4xx(app, monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None, headers=None):
        calls.append(1)
        return FakeResponse(404)

    monkeypatch.setattr(http.requests, "get", fake_get)
    monkeypatch.setattr(http.time, "sleep", lambda seconds: None)
    with app.app_context(), pytest.raises(WeatherError):
        http.get("http://proveedor")
    assert len(calls) == 1


def test_get_retries_on_429(app, monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None, headers=None):
        calls.append(1)
        return FakeResponse(429) if len(calls) < 2 else FakeResponse(200, {"ok": True})

    monkeypatch.setattr(http.requests, "get", fake_get)
    monkeypatch.setattr(http.time, "sleep", lambda seconds: None)
    with app.app_context():
        assert http.get("http://proveedor").json() == {"ok": True}
    assert len(calls) == 2


def test_get_gives_up_after_retries(app, monkeypatch):
    def fake_get(url, params=None, timeout=None, headers=None):
        raise requests.ConnectionError("sin red")

    monkeypatch.setattr(http.requests, "get", fake_get)
    monkeypatch.setattr(http.time, "sleep", lambda seconds: None)
    with app.app_context(), pytest.raises(WeatherError):
        http.get("http://proveedor")
