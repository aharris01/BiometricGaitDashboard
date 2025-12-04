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


# ---------------------------------------------------------
# fetch_participants callback
# ---------------------------------------------------------


class TestFetchParticipants:
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "value, expected_options, expected_first",
        [
            pytest.param(
                [101],
                [{"label": "101", "value": 101}],
                101,
                id="single participant",
            ),
            pytest.param(
                [101, 202, 303],
                [
                    {"label": "101", "value": 101},
                    {"label": "202", "value": 202},
                    {"label": "303", "value": 303},
                ],
                101,
                id="multiple participants",
            ),
            pytest.param(
                [],
                [],
                None,
                id="no participants",
            ),
        ],
    )
    def test_success(self, monkeypatch, value, expected_options, expected_first):
        captured = {}

        # 👇 use the parametrized `value` here
        monkeypatch.setattr(
            app_mod.requests,
            "get",
            make_fake_get({"items": value}, captured=captured),
        )

        options, first_value = app_mod.fetch_participants(None)

        assert options == expected_options
        assert first_value == expected_first
        assert captured["url"] == f"{app_mod.API_BASE}/api/participants"
        assert captured["timeout"] == 5


# ---------------------------------------------------------
# fetch_dates / fetch_directions / fetch_events helpers
# ---------------------------------------------------------


class TestFetchDates:
    @pytest.mark.unit
    def test_success(self, monkeypatch):
        captured = {}

        monkeypatch.setattr(
            app_mod.requests,
            "get",
            make_fake_get(
                {"items": ["2024-01-01", "2024-01-02"]},  # 👈 use strings here
                captured=captured,
            ),
        )

        participant = "3"
        result = app_mod.fetch_dates(participant)
        assert result == [
            {"label": "2024-01-01", "value": "2024-01-01"},
            {"label": "2024-01-02", "value": "2024-01-02"},
        ]
        assert (
            captured["url"]
            == f"{app_mod.API_BASE}/api/participants/{participant}/dates"
        )
        assert captured["timeout"] == 5


class TestFetchDirections:
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
        result = app_mod.fetch_directions(participant, datestr)
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
        "participant, datestr",
        [
            (None, "2024-01-01"),
            ("3", None),
            (None, None),
        ],
    )
    def test_no_parameters_raises(self, participant, datestr):
        with pytest.raises(app_mod.PreventUpdate):
            app_mod.fetch_directions(participant, datestr)


class TestFetchEvents:
    @pytest.mark.unit
    def test_success(self, monkeypatch):
        captured = {}

        monkeypatch.setattr(
            app_mod.requests,
            "get",
            make_fake_get({"items": [1, 2]}, captured=captured),  # 👈 ints, not strings
        )

        participant = "3"
        datestr = "2024-01-01"
        direction = "in"
        result = app_mod.fetch_events(participant, datestr, direction)
        assert result == [
            {"label": "1", "value": 1},
            {"label": "2", "value": 2},
        ]
        assert (
            captured["url"]
            == f"{app_mod.API_BASE}/api/participants/{participant}/dates/{datestr}/directions/{direction}/events"
        )
        assert captured["timeout"] == 5


# ---------------------------------------------------------
# getSwipeEventId callback
# ---------------------------------------------------------


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

        # n_clicks arg is unused
        result = app_mod.getSwipeEventId(None, participant, datestr, direction, event)

        # Callback returns the store data dict
        assert result == {"event_id": "123_2024-01-09_out_4"}
        assert (
            captured["url"]
            == f"{app_mod.API_BASE}/api/swipe/{participant}/{datestr}/{direction}/{event}"
        )
        assert captured["timeout"] == 5

    @pytest.mark.unit
    def test_missing_values_raises(self):
        with pytest.raises(app_mod.PreventUpdate):
            app_mod.getSwipeEventId(None, None, "2024-01-09", "out", 4)


# ---------------------------------------------------------
# Utility helpers: fetch_json / require_values
# ---------------------------------------------------------


class TestUtilFunctions:
    @pytest.mark.unit
    def test_fetch_json_http_error(self, monkeypatch):
        monkeypatch.setattr(
            app_mod.requests,
            "get",
            make_fake_get({}, status_ok=False),
        )

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
        app_mod.require_values(
            context="All values present",
            participant="100",
            date="2023-01-09",
            direction="in",
        )

    @pytest.mark.unit
    def test_require_values_missing_raises(self):
        with pytest.raises(app_mod.PreventUpdate):
            app_mod.require_values(
                context="Missing value",
                participant=None,
                date="2023-01-09",
            )


class TestDisplaySummaryGraph:
    @pytest.mark.unit
    def test_display_summary_graph_success(self, monkeypatch):
        """
        display_summary_graph should:
        - call fetch_json three times (p100, grf, footsteps)
        - return a Dash layout and the footsteps list
        """

        calls = []

        def fake_fetch_json(url, timeout=5, context=""):
            calls.append((url, context))
            if url.endswith("/p100"):
                return {"p100": [[1, 2], [3, 4]]}
            if url.endswith("/grf"):
                return {"grf": [0.1, 0.2, 0.3]}
            if url.endswith("/footsteps/data"):
                return [{"id": 0, "x_min": 0, "x_max": 1, "y_min": 0, "y_max": 1}]
            raise AssertionError(f"Unexpected URL: {url}")

        monkeypatch.setattr(app_mod, "fetch_json", fake_fetch_json)

        view, footsteps = app_mod.display_summary_graph({"event_id": "evt-123"})

        # We should have called fetch_json three times
        assert len(calls) == 3
        assert calls[0][1] == "getEventP100"
        assert calls[1][1] == "getEventGRF"
        assert calls[2][1] == "getFootsteps"

        # Returned layout + footsteps
        from dash import html

        assert isinstance(view, html.Div)
        assert isinstance(footsteps, list)
        assert footsteps[0]["id"] == 0


class TestShowSelectedStep:
    @pytest.mark.unit
    def test_show_selected_step_success(self, monkeypatch):
        """
        show_selected_step should:
        - find the clicked footstep
        - call backend for per-step data
        - return updated figures
        """

        # Fake per-step backend data
        def fake_fetch_json(url, timeout=5, context=""):
            assert "footsteps" in url
            return {
                "p100": [[1.0, 2.0], [3.0, 4.0]],
                "grf": [0.5, 0.6, 0.7],
            }

        monkeypatch.setattr(app_mod, "fetch_json", fake_fetch_json)

        # Click in the middle of the step bounding box
        clickData = {"points": [{"x": 5.0, "y": 5.0}]}

        # Base figure for the main P100 graph
        import numpy as np
        import plotly.express as px

        base_fig = px.imshow(np.zeros((10, 10)))
        figure_dict = base_fig.to_dict()

        # One footstep bounding box from (0,0) to (10,10)
        footsteps = [
            {"id": 1, "x_min": 0, "x_max": 10, "y_min": 0, "y_max": 10},
        ]

        event_store = {"event_id": "evt-123"}

        fig, step_p100_fig, step_grf_fig = app_mod.show_selected_step(
            clickData, figure_dict, footsteps, event_store
        )

        # Main P100 fig should now have a shape (the selection rectangle)
        assert "layout" in fig
        assert "shapes" in fig["layout"]
        assert len(fig["layout"]["shapes"]) == 1
        rect = fig["layout"]["shapes"][0]
        assert rect["x0"] == 0 and rect["x1"] == 10

        # Step P100 figure should have some data
        assert "data" in step_p100_fig
        assert len(step_p100_fig["data"]) >= 1

        # Step GRF figure should have a line trace
        assert "data" in step_grf_fig
        assert len(step_grf_fig["data"]) >= 1
