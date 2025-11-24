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


def make_fake_get(response_data, *, status_ok=True, captured=None):
    def fake_get(url, timeout):
        if captured is not None:
            captured["url"] = url
            captured["timeout"] = timeout
        return StubResponse(response_data, status_ok=status_ok)

    return fake_get


class TestGetParticipants:
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "value, expected",
        [
            pytest.param(
                [101], [{"label": "101", "value": 101}], id="single participant"
            ),
            pytest.param(
                [101, 202, 303],
                [
                    {"label": "101", "value": 101},
                    {"label": "202", "value": 202},
                    {"label": "303", "value": 303},
                ],
                id="multiple participants sorted",
            ),
            pytest.param([], [], id="no participants"),
        ],
    )
    def test_success(self, monkeypatch, value, expected):
        captured = {}

        monkeypatch.setattr(
            app_mod.requests,
            "get",
            make_fake_get({"items": value}, captured=captured),
        )

        result = app_mod.getParticipants(None)
        assert result == expected
        assert captured["url"] == f"{app_mod.API_BASE}/api/participants"
        assert captured["timeout"] == 5


class TestGetDates:
    @pytest.mark.unit
    def test_success(self, monkeypatch):
        captured = {}

        monkeypatch.setattr(
            app_mod.requests,
            "get",
            make_fake_get({"items": ["2024-01-01", "2024-01-02"]}, captured=captured),
        )

        participant = "3"
        result = app_mod.getDates(participant)
        assert result == [
            {"label": "2024-01-01", "value": "2024-01-01"},
            {"label": "2024-01-02", "value": "2024-01-02"},
        ]
        assert (
            captured["url"]
            == f"{app_mod.API_BASE}/api/participants/{participant}/dates"
        )
        assert captured["timeout"] == 5

    @pytest.mark.unit
    def test_no_parameters(self):
        with pytest.raises(app_mod.PreventUpdate):
            app_mod.getDates(None)


class TestGetDirections:
    @pytest.mark.unit
    def test_success(self, monkeypatch):
        captured = {}

        monkeypatch.setattr(
            app_mod.requests,
            "get",
            make_fake_get({"items": ["in", "out"]}, captured=captured),
        )

        participant = "3"
        datestr = "2024-01-01"
        result = app_mod.getDirections(participant, datestr)
        assert result == [
            {"label": "in", "value": "in"},
            {"label": "out", "value": "out"},
        ]
        assert (
            captured["url"]
            == f"{app_mod.API_BASE}/api/participants/{participant}/dates/{datestr}/directions"
        )
        assert captured["timeout"] == 5

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "values", [(None, "2024-01-01"), ("3", None), (None, None)]
    )
    def test_no_parameters(self, values):
        with pytest.raises(app_mod.PreventUpdate):
            app_mod.getDirections(None, "2024-01-01")
            app_mod.getDirections("3", None)
            app_mod.getDirections(None, None)


class TestGetEvents:
    @pytest.mark.unit
    def test_success(self, monkeypatch):
        captured = {}

        monkeypatch.setattr(
            app_mod.requests,
            "get",
            make_fake_get({"items": ["1", "2"]}, captured=captured),
        )

        participant = "3"
        datestr = "2024-01-01"
        direction = "in"
        result = app_mod.getEvents(participant, datestr, direction)
        assert result == [
            {"label": "1", "value": "1"},
            {"label": "2", "value": "2"},
        ]
        assert (
            captured["url"]
            == f"{app_mod.API_BASE}/api/participants/{participant}/dates/{datestr}/directions/{direction}/events"
        )
        assert captured["timeout"] == 5

    @pytest.mark.unit
    def test_no_parameters(self):
        with pytest.raises(app_mod.PreventUpdate):
            app_mod.getEvents(None, "2024-01-01", "in")
            app_mod.getEvents("3", None, "in")
            app_mod.getEvents("3", "2024-01-01", None)


class TestGetSwipeEventId:
    @pytest.mark.unit
    def test_success(self, monkeypatch):
        captured = {}

        monkeypatch.setattr(
            app_mod.requests,
            "get",
            make_fake_get({"id": "123_2024-01-09_out_4"}, captured=captured),
        )

        participant = 123
        datestr = "2024-01-09"
        direction = "out"
        event = 4
        result = app_mod.getSwipeEventId(None, participant, datestr, direction, event)
        assert result == (
            "Swipe Event ID: 123_2024-01-09_out_4",
            {"event_id": "123_2024-01-09_out_4"},
        )
        assert (
            captured["url"]
            == f"{app_mod.API_BASE}/api/swipe/{participant}/{datestr}/{direction}/{event}"
        )
        assert captured["timeout"] == 5


class TestUtilFunctions:
    @pytest.mark.unit
    def test_fetch_json_http_error(self, monkeypatch):
        monkeypatch.setattr(app_mod.requests, "get", make_fake_get({}, status_ok=False))

        with pytest.raises(app_mod.PreventUpdate):
            app_mod.fetch_json("http://example.com/api", context="test")

    @pytest.mark.unit
    def test_fetch_json_success(self, monkeypatch):
        expected_data = {"key": "value"}
        monkeypatch.setattr(
            app_mod.requests,
            "get",
            make_fake_get(expected_data, status_ok=True),
        )

        result = app_mod.fetch_json("http://example.com/api", context="test")
        assert result == expected_data

    @pytest.mark.unit
    def test_require_values_all_present(self):
        # Should not raise
        app_mod.require_values("a", "b", "c")
