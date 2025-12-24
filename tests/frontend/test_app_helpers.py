# tests/frontend/test_app_helpers.py
import pytest
from dash import no_update

import frontend.callbacks.dropdowns as dd


class TestFetchOptionsForLevel:
    @pytest.mark.unit
    def test_fetch_dates_branch(self, monkeypatch):
        def fake_get_dates(participant, logger=None):
            return ["d1", "d2"]

        monkeypatch.setattr(dd, "get_dates", fake_get_dates)

        upstream = {4: 1001}
        out = dd._fetch_options_for_level(3, upstream, logger=None)
        assert out == ["d1", "d2"]

    @pytest.mark.unit
    def test_fetch_directions_branch(self, monkeypatch):
        def fake_get_directions(participant, datestr, logger=None):
            return ["in", "out"]

        monkeypatch.setattr(dd, "get_directions", fake_get_directions)

        upstream = {4: 1001, 3: "2024-10-01"}
        out = dd._fetch_options_for_level(2, upstream, logger=None)
        assert out == ["in", "out"]

    @pytest.mark.unit
    def test_fetch_events_branch(self, monkeypatch):
        def fake_get_events(participant, datestr, direction, logger=None):
            return [1, 2, 3]

        monkeypatch.setattr(dd, "get_events", fake_get_events)

        upstream = {4: 1001, 3: "2024-10-01", 2: "in"}
        out = dd._fetch_options_for_level(1, upstream, logger=None)
        assert out == [1, 2, 3]

    @pytest.mark.unit
    def test_fetch_options_for_level_default_empty(self):
        out = dd._fetch_options_for_level(99, {}, logger=None)
        assert out == []


class TestCalculateCascadeState:
    @pytest.mark.unit
    def test_cascade_when_trigger_has_value(self, monkeypatch):
        def fake_fetch(target_level, upstream, logger):
            return ["opt-a", "opt-b"]

        monkeypatch.setattr(dd, "_fetch_options_for_level", fake_fetch)

        all_ids = [{"level": 4}, {"level": 3}, {"level": 2}, {"level": 1}]
        all_values = [1001, "2024-10-01", None, None]
        triggered_id = {"level": 3}

        new_values, new_options = dd._calculate_cascade_state(
            triggered_id, all_ids, all_values, logger=None
        )

        assert new_values[0] is no_update
        assert new_options[0] is no_update

        assert new_values[1] is no_update
        assert new_options[1] is no_update

        assert new_values[2] is None
        assert new_options[2] == ["opt-a", "opt-b"]

        assert new_values[3] is no_update
        assert new_options[3] is no_update

    @pytest.mark.unit
    def test_cascade_when_trigger_cleared(self):
        all_ids = [{"level": 4}, {"level": 3}, {"level": 2}]
        all_values = [1001, None, "in"]
        triggered_id = {"level": 3}

        new_values, new_options = dd._calculate_cascade_state(
            triggered_id, all_ids, all_values, logger=None
        )

        assert new_values[2] is None
        assert new_options[2] == []
