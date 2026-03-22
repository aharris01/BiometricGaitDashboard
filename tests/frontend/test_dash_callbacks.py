# tests/test_dash_callbacks.py
import pytest
import requests

from dash.exceptions import PreventUpdate

import frontend.api as api
from frontend.callbacks.footsteps import _resolve_draft_depth_range, _review_label_value
from frontend.utils import require_values

pytestmark = pytest.mark.unit


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


def test_fetch_json_success(monkeypatch):
    expected_data = {"key": "value"}
    monkeypatch.setattr(
        api.requests, "get", make_fake_get(expected_data, status_ok=True)
    )
    out = api.fetch_json("http://example.com/api", context="test")
    assert out == expected_data


def test_fetch_json_http_error(monkeypatch):
    monkeypatch.setattr(api.requests, "get", make_fake_get({}, status_ok=False))
    with pytest.raises(PreventUpdate):
        api.fetch_json("http://example.com/api", context="test")


def test_get_participants(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        api.requests, "get", make_fake_get({"items": [101, 202]}, captured=captured)
    )
    out = api.get_participants()
    assert out == [{"label": "101", "value": 101}, {"label": "202", "value": 202}]
    assert captured["url"].endswith("/api/participants")


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


def test_require_values_missing_raises():
    with pytest.raises(PreventUpdate):
        require_values(context="Missing", participant=None, datestr="2024-01-01")


def test_require_values_all_present_ok():
    require_values(
        context="All present",
        participant=1,
        datestr="2024-01-01",
        direction="in",
        event=1,
    )


def test_resolve_draft_depth_range_resets_to_full_span_for_new_draft():
    out = _resolve_draft_depth_range(
        slider_max=101,
        depth_range=[0, 0],
        reset_range=True,
    )

    assert out == [0, 101]


def test_resolve_draft_depth_range_preserves_manual_slider_selection():
    out = _resolve_draft_depth_range(
        slider_max=101,
        depth_range=[12, 48],
        reset_range=False,
    )

    assert out == [12, 48]


# ------------------------------------------------------------
# Tests for increasing coverage (frontend/api.py)
# ------------------------------------------------------------


class FakeLogger:
    # Simple logger stub to verify error logging branch
    def __init__(self):
        self.logged = False

    def error(self, msg):
        self.logged = True


def test_get_dates(monkeypatch):
    # Ensure get_dates correctly formats API response into dropdown options
    monkeypatch.setattr(
        api.requests,
        "get",
        make_fake_get({"items": ["2024-01-01"]}),
    )

    out = api.get_dates(1)

    assert out == [{"label": "2024-01-01", "value": "2024-01-01"}]


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


def test_get_available_metrics(monkeypatch):
    # Ensure available metrics endpoint returns raw JSON payload
    monkeypatch.setattr(
        api.requests,
        "get",
        make_fake_get({"items": ["avg_bbox_size", "step_count"]}),
    )

    out = api.get_available_metrics()

    assert out == {"items": ["avg_bbox_size", "step_count"]}


def test_get_event_footstep_p100s(monkeypatch):
    # Ensure footstep thumbnail endpoint returns raw JSON payload
    monkeypatch.setattr(
        api.requests,
        "get",
        make_fake_get({"items": []}),
    )

    out = api.get_event_footstep_p100s("evt-1")

    assert out == {"items": []}


def test_create_draft_footstep_posts_bbox(monkeypatch):
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return StubResponse({"depth": 3, "volume": [[[1]], [[2]], [[3]]]})

    monkeypatch.setattr(api.requests, "post", fake_post)

    out = api.create_draft_footstep(
        "evt-1",
        x_min=1,
        x_max=5,
        y_min=2,
        y_max=6,
    )

    assert captured["url"].endswith("/api/footsteps/evt-1/draft")
    assert captured["json"] == {
        "x_min": 1,
        "x_max": 5,
        "y_min": 2,
        "y_max": 6,
    }
    assert out["depth"] == 3


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


def test_get_date_part_invalid_part():
    out = api.get_date_part("invalid_part")
    assert out == []


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


def test_review_label_value_normalizes_none_to_empty_string():
    assert _review_label_value(None) == ""
    assert _review_label_value("") == ""
    assert _review_label_value("Left") == "Left"


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


def test_search_footsteps_builds_all_filter_params(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        api.requests,
        "get",
        make_fake_get({"items": [], "total": 0}, captured=captured),
    )

    out = api.search_footsteps(
        event_ids=["evt-1", "evt-2"],
        participants=[11111, 22222],
        date_from="2025-01-01",
        date_to="2025-01-31",
        width_min=10,
        width_max=20,
        height_min=15,
        height_max=30,
        size_min=100,
        size_max=500,
        offset=10,
        limit=25,
    )

    assert out == {"items": [], "total": 0}
    assert captured["url"].endswith("/api/footsteps/search")
    assert captured["params"] == {
        "offset": 10,
        "limit": 25,
        "event_ids": "evt-1,evt-2",
        "participants": "11111,22222",
        "date_from": "2025-01-01",
        "date_to": "2025-01-31",
        "width_min": 10,
        "width_max": 20,
        "height_min": 15,
        "height_max": 30,
        "size_min": 100,
        "size_max": 500,
    }


def test_create_footstep_api(monkeypatch):
    monkeypatch.setattr(
        api.requests,
        "post",
        lambda url, json=None, timeout=None: StubResponse(
            {
                "item": {"event_id": "evt-1", "footstep_id": 9},
                "bbox": {"x_min": 1, "x_max": 2, "y_min": 3, "y_max": 4},
            }
        ),
    )

    out = api.create_footstep(
        "evt-1",
        start_frame=1,
        end_frame=2,
        x_min=10,
        x_max=20,
        y_min=30,
        y_max=40,
        label="new",
    )

    assert out["item"]["event_id"] == "evt-1"
    assert out["item"]["footstep_id"] == 9


def test_delete_footstep_api(monkeypatch):
    monkeypatch.setattr(
        api.requests,
        "post",
        lambda url, json=None, timeout=None: StubResponse(
            {"ok": True, "event_id": "evt-1", "footstep_id": 7}
        ),
    )

    out = api.delete_footstep("evt-1", 7)

    assert out == {"ok": True, "event_id": "evt-1", "footstep_id": 7}
