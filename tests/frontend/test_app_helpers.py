import pytest
from dash import no_update

import frontend.app as app_mod


# --------------------------------------------------------------------
# calculate_cascade_state
# --------------------------------------------------------------------


class TestCalculateCascadeState:
    @pytest.mark.unit
    def test_cascade_when_trigger_has_value(self, monkeypatch):
        """
        When a dropdown at level 3 (date) changes and has a value,
        level 2 (direction) should be reset to None and get new options,
        while unrelated levels remain no_update.
        """
        captured = {}

        def fake_fetch_options_for_level(target_level, upstream_selections):
            captured["target_level"] = target_level
            captured["upstream"] = upstream_selections
            return ["opt-a", "opt-b"]

        monkeypatch.setattr(
            app_mod, "fetch_options_for_level", fake_fetch_options_for_level
        )

        # Four dropdowns: level 4 (participant), 3 (date), 2 (direction), 1 (event)
        all_ids = [
            {"level": 4},
            {"level": 3},
            {"level": 2},
            {"level": 1},
        ]
        all_values = [
            1001,             # participant
            "2024-10-01",     # date (trigger)
            None,             # direction
            None,             # event
        ]

        triggered_id = {"level": 3}

        new_values, new_options = app_mod.calculate_cascade_state(
            triggered_id=triggered_id,
            all_ids=all_ids,
            all_values=all_values,
        )

        # Level 4: unchanged (no_update)
        assert new_values[0] is no_update
        assert new_options[0] is no_update

        # Level 3 (trigger): unchanged (no_update)
        assert new_values[1] is no_update
        assert new_options[1] is no_update

        # Level 2 (just below trigger): reset & repopulated
        assert new_values[2] is None
        assert new_options[2] == ["opt-a", "opt-b"]

        # Level 1 (below that): untouched as it was already None (no_update)
        assert new_values[3] is no_update
        assert new_options[3] is no_update

        # fetch_options_for_level called with target_level == 2 and current selections
        assert captured["target_level"] == 2
        # upstream selections keyed by level
        assert captured["upstream"][4] == 1001
        assert captured["upstream"][3] == "2024-10-01"

    @pytest.mark.unit
    def test_cascade_when_trigger_cleared(self, monkeypatch):
        """
        If the trigger dropdown value is cleared (None),
        the next level's value should reset to None and options → [].
        """
        # We don't expect fetch_options_for_level to be called in this path,
        # so we can just ensure it's not accidentally used.
        monkeypatch.setattr(
            app_mod, "fetch_options_for_level", lambda *args, **kwargs: ["should-not"]
        )

        all_ids = [
            {"level": 4},
            {"level": 3},
            {"level": 2},
        ]
        all_values = [
            1001,     # participant
            None,     # date: trigger value is None
            "in",     # direction (should be reset)
        ]
        triggered_id = {"level": 3}

        new_values, new_options = app_mod.calculate_cascade_state(
            triggered_id=triggered_id,
            all_ids=all_ids,
            all_values=all_values,
        )

        # Level 4: unchanged
        assert new_values[0] is no_update
        assert new_options[0] is no_update

        # Level 3: unchanged
        assert new_values[1] is no_update
        assert new_options[1] is no_update

        # Level 2 (just below trigger): cleared and options emptied
        assert new_values[2] is None
        assert new_options[2] == []


# --------------------------------------------------------------------
# fetch_options_for_level
# --------------------------------------------------------------------


class TestFetchOptionsForLevel:
    @pytest.mark.unit
    def test_fetch_dates_branch(self, monkeypatch):
        captured = {}

        def fake_fetch_dates(participant):
            captured["participant"] = participant
            return ["d1", "d2"]

        monkeypatch.setattr(app_mod, "fetch_dates", fake_fetch_dates)

        upstream = {4: 1001}  # level 4 -> participant
        out = app_mod.fetch_options_for_level(target_level=3, upstream_selections=upstream)

        assert out == ["d1", "d2"]
        assert captured["participant"] == 1001

    @pytest.mark.unit
    def test_fetch_directions_branch(self, monkeypatch):
        captured = {}

        def fake_fetch_directions(participant, datestr):
            captured["participant"] = participant
            captured["datestr"] = datestr
            return ["in", "out"]

        monkeypatch.setattr(app_mod, "fetch_directions", fake_fetch_directions)

        upstream = {4: 1001, 3: "2024-10-01"}  # participant + date
        out = app_mod.fetch_options_for_level(target_level=2, upstream_selections=upstream)

        assert out == ["in", "out"]
        assert captured["participant"] == 1001
        assert captured["datestr"] == "2024-10-01"

    @pytest.mark.unit
    def test_fetch_events_branch(self, monkeypatch):
        captured = {}

        def fake_fetch_events(participant, datestr, direction):
            captured["participant"] = participant
            captured["datestr"] = datestr
            captured["direction"] = direction
            return [1, 2, 3]

        monkeypatch.setattr(app_mod, "fetch_events", fake_fetch_events)

        upstream = {
            4: 1001,
            3: "2024-10-01",
            2: "in",
        }
        out = app_mod.fetch_options_for_level(target_level=1, upstream_selections=upstream)

        assert out == [1, 2, 3]
        assert captured["participant"] == 1001
        assert captured["datestr"] == "2024-10-01"
        assert captured["direction"] == "in"

    @pytest.mark.unit
    def test_fetch_options_for_level_default_empty(self):
        # No matching branch -> should return []
        upstream = {}
        out = app_mod.fetch_options_for_level(target_level=99, upstream_selections=upstream)
        assert out == []


# --------------------------------------------------------------------
# parse_date_str
# --------------------------------------------------------------------


class TestParseDateStr:
    @pytest.mark.unit
    def test_valid_date_str(self):
        assert app_mod.parse_date_str("2024-01-01") is True

    @pytest.mark.unit
    def test_invalid_date_str(self):
        assert app_mod.parse_date_str("2024-13-40") is False


# --------------------------------------------------------------------
# show_selected_step early exits
# --------------------------------------------------------------------


class TestShowSelectedStepEarlyExit:
    @pytest.mark.unit
    def test_no_clickdata_raises_prevent_update(self):
        with pytest.raises(app_mod.PreventUpdate):
            app_mod.show_selected_step(
                clickData=None,
                figure={},
                footsteps=[{"id": 1, "x_min": 0, "x_max": 10, "y_min": 0, "y_max": 10}],
                event_store={"event_id": "evt-1"},
            )

    @pytest.mark.unit
    def test_missing_event_id_raises_prevent_update(self):
        clickData = {"points": [{"x": 5.0, "y": 5.0}]}
        footsteps = [{"id": 1, "x_min": 0, "x_max": 10, "y_min": 0, "y_max": 10}]
        # event_store without event_id
        event_store = {}

        with pytest.raises(app_mod.PreventUpdate):
            app_mod.show_selected_step(
                clickData=clickData,
                figure={},
                footsteps=footsteps,
                event_store=event_store,
            )
