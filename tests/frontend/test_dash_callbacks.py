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
    def fake_get(url, params=None, timeout=None):
        if captured is not None:
            captured["url"] = url
            captured["params"] = params
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
    }
    monkeypatch.setattr(api.requests, "get", make_fake_get(payload, captured=captured))
    out = api.get_event_full("evt-1")
    assert out["event"]["event_id"] == "evt-1"
    assert "footsteps" in out
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


# ------------------------------------------------------------
# Tests for increasing coverage (frontend/api.py)
# ------------------------------------------------------------


class FakeLogger:
    # Simple logger stub to verify error logging branch
    def __init__(self):
        self.logged = False

    def error(self, msg):
        self.logged = True


@pytest.mark.unit
def test_get_dates(monkeypatch):
    # Ensure get_dates correctly formats API response into dropdown options
    monkeypatch.setattr(
        api.requests,
        "get",
        make_fake_get({"items": ["2024-01-01"]}),
    )

    out = api.get_dates(1)

    assert out == [{"label": "2024-01-01", "value": "2024-01-01"}]


@pytest.mark.unit
def test_get_directions(monkeypatch):
    # Ensure get_directions correctly maps returned direction values
    monkeypatch.setattr(
        api.requests,
        "get",
        make_fake_get({"items": ["in", "out"]}),
    )

    out = api.get_directions(1, "2024-01-01")

    assert out == [
        {"label": "in", "value": "in"},
        {"label": "out", "value": "out"},
    ]


@pytest.mark.unit
def test_get_events(monkeypatch):
    # Ensure get_events converts integer events into dropdown options
    monkeypatch.setattr(
        api.requests,
        "get",
        make_fake_get({"items": [1, 2]}),
    )

    out = api.get_events(1, "2024-01-01", "in")

    assert out == [
        {"label": "1", "value": 1},
        {"label": "2", "value": 2},
    ]


@pytest.mark.unit
def test_get_swipe_event_summary_metrics(monkeypatch):
    # Ensure summary metric request builds correct query parameters
    captured = {}

    monkeypatch.setattr(
        api.requests,
        "get",
        make_fake_get({"EVT1": {"avg_bbox_size": 10}}, captured=captured),
    )

    out = api.get_swipe_event_summary_metrics(
        "avg_bbox_size",
        "step_count",
        filters={"participants": [100, 200]},
    )

    # Confirm participant filter was added to URL
    assert captured["params"]["participants"] == "100,200"
    assert captured["params"]["x"] == "avg_bbox_size"
    assert captured["params"]["y"] == "step_count"

    # Confirm returned data is passed through unchanged
    assert out == {"EVT1": {"avg_bbox_size": 10}}


@pytest.mark.unit
def test_get_available_metrics(monkeypatch):
    # Ensure available metrics endpoint returns raw JSON payload
    monkeypatch.setattr(
        api.requests,
        "get",
        make_fake_get({"items": ["avg_bbox_size", "step_count"]}),
    )

    out = api.get_available_metrics()

    assert out == {"items": ["avg_bbox_size", "step_count"]}


@pytest.mark.unit
def test_get_event_footstep_p100s(monkeypatch):
    # Ensure footstep thumbnail endpoint returns raw JSON payload
    monkeypatch.setattr(
        api.requests,
        "get",
        make_fake_get({"items": []}),
    )

    out = api.get_event_footstep_p100s("evt-1")

    assert out == {"items": []}


@pytest.mark.unit
def test_fetch_json_logs_on_error(monkeypatch):
    # Ensure fetch_json logs error details when a request fails
    logger = FakeLogger()

    monkeypatch.setattr(
        api.requests,
        "get",
        make_fake_get({}, status_ok=False),
    )

    with pytest.raises(PreventUpdate):
        api.fetch_json("http://example.com", logger=logger)

    assert logger.logged is True


@pytest.mark.unit
def test_fetch_json_non_json_error_body(monkeypatch):
    class BadJSONResponse:
        def raise_for_status(self):
            raise requests.HTTPError("error")

        def json(self):
            raise ValueError("not json")

    def fake_get(*args, **kwargs):
        return BadJSONResponse()

    monkeypatch.setattr(api.requests, "get", fake_get)

    with pytest.raises(PreventUpdate):
        api.fetch_json("http://example.com/api")


@pytest.mark.unit
def test_get_date_part_invalid_part():
    out = api.get_date_part("invalid_part")
    assert out == []


@pytest.mark.unit
def test_get_date_part_with_filters(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        api.requests,
        "get",
        make_fake_get({"items": [2024]}, captured=captured),
    )

    out = api.get_date_part(
        "year",
        participants=[1, 2],
        year=2024,
        month=5,
    )

    assert captured["params"]["participants"] == "1,2"
    assert captured["params"]["year"] == 2024
    assert captured["params"]["month"] == 5
    assert out == {"items": [2024]}


@pytest.mark.unit
def test_fetch_json_error_with_json_body(monkeypatch):
    class ErrorResponse:
        def __init__(self):
            self._json = {"message": "bad", "details": "more"}

        def raise_for_status(self):
            err = requests.HTTPError("error")
            err.response = self
            raise err

        def json(self):
            return self._json

    def fake_get(*args, **kwargs):
        return ErrorResponse()

    monkeypatch.setattr(api.requests, "get", fake_get)

    with pytest.raises(PreventUpdate):
        api.fetch_json("http://example.com/api")


@pytest.mark.unit
def test_get_date_part_day(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        api.requests,
        "get",
        make_fake_get({"items": [1]}, captured=captured),
    )

    out = api.get_date_part("day")

    assert captured["url"].endswith("/api/events/days")
    assert out == {"items": [1]}
