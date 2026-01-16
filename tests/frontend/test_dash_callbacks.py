# tests/test_dash_callbacks.py
import pytest
import requests

from dash.exceptions import PreventUpdate

import frontend.api as api
from frontend.utils import require_values


class StubResponse:
    def __init__(self, json_data, status_ok=True):
        self._json_data = json_data
        self._status_ok = status_ok

    def raise_for_status(self):
        if not self._status_ok:
            raise requests.HTTPError("error")

    def json(self):
        return self._json_data


def make_fake_get(response_data, *, status_ok=True, captured=None):
    def fake_get(url, timeout):
        if captured is not None:
            captured["url"] = url
            captured["timeout"] = timeout
        return StubResponse(response_data, status_ok=status_ok)

    return fake_get


@pytest.mark.unit
def test_fetch_json_success(monkeypatch):
    expected_data = {"key": "value"}
    monkeypatch.setattr(
        api.requests, "get", make_fake_get(expected_data, status_ok=True)
    )
    out = api.fetch_json("http://example.com/api", context="test")
    assert out == expected_data


@pytest.mark.unit
def test_fetch_json_http_error(monkeypatch):
    monkeypatch.setattr(api.requests, "get", make_fake_get({}, status_ok=False))
    with pytest.raises(PreventUpdate):
        api.fetch_json("http://example.com/api", context="test")


@pytest.mark.unit
def test_get_participants(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        api.requests, "get", make_fake_get({"items": [101, 202]}, captured=captured)
    )
    out = api.get_participants()
    assert out == [{"label": "101", "value": 101}, {"label": "202", "value": 202}]
    assert captured["url"].endswith("/api/participants")


@pytest.mark.unit
def test_get_event_full(monkeypatch):
    captured = {}
    payload = {
        "event": {"event_id": "evt-1"},
        "availability": {},
        "p100": [[1]],
        "grf": [0.1],
        "footsteps": [],
        "footstep_details": [],
    }
    monkeypatch.setattr(api.requests, "get", make_fake_get(payload, captured=captured))
    out = api.get_event_full("evt-1")
    assert out["event"]["event_id"] == "evt-1"
    assert "footstep_details" in out
    assert captured["url"].endswith("/api/events/evt-1/full")


@pytest.mark.unit
def test_require_values_missing_raises():
    with pytest.raises(PreventUpdate):
        require_values(context="Missing", participant=None, datestr="2024-01-01")


@pytest.mark.unit
def test_require_values_all_present_ok():
    require_values(
        context="All present",
        participant=1,
        datestr="2024-01-01",
        direction="in",
        event=1,
    )
