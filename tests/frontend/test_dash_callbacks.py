import builtins
import types
import pytest
import requests

import frontend.app as app_mod


class StubResponse:
    def __init__(self, json_data, status_ok=True):
        self._json_data = json_data
        self._status_ok = status_ok
        self.raise_called = False

    def raise_for_status(self):
        self.raise_called = True
        if not self._status_ok:
            raise requests.HTTPError("error")

    def json(self):
        return self._json_data


def test_getParticipants_success(monkeypatch):
    captured = {}

    def fake_get(url, timeout):
        captured["url"] = url
        captured["timeout"] = timeout
        return StubResponse([101, 202, "303"], status_ok=True)

    monkeypatch.setattr(app_mod.requests, "get", fake_get)

    result = app_mod.getParticipants(None)
    assert result == [
        {"label": "101", "value": 101},
        {"label": "202", "value": 202},
        {"label": "303", "value": "303"},
    ]
    assert captured["url"] == f"{app_mod.API_BASE}/api/participants"
    assert captured["timeout"] == 5


def test_getParticipants_http_error(monkeypatch):
    def fake_get(url, timeout):
        return StubResponse([], status_ok=False)

    monkeypatch.setattr(app_mod.requests, "get", fake_get)

    with pytest.raises(requests.HTTPError):
        app_mod.getParticipants(None)


def test_getDates_success(monkeypatch):
    captured = {}

    def fake_get(url, timeout):
        captured["url"] = url
        captured["timeout"] = timeout
        return StubResponse(["2024-01-01", "2024-01-02"])

    monkeypatch.setattr(app_mod.requests, "get", fake_get)

    participant = "3"
    result = app_mod.getDates(participant)
    assert result == [
        {"label": "2024-01-01", "value": "2024-01-01"},
        {"label": "2024-01-02", "value": "2024-01-02"},
    ]
    assert captured["url"] == f"{app_mod.API_BASE}/api/participants/{participant}/dates"
    assert captured["timeout"] == 5


def test_getDates_http_error(monkeypatch):
    def fake_get(url, timeout):
        return StubResponse([], status_ok=False)

    monkeypatch.setattr(app_mod.requests, "get", fake_get)

    with pytest.raises(requests.HTTPError):
        app_mod.getDates("5")
