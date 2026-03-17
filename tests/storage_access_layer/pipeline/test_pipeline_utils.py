import pathlib

import numpy as np
import pandas as pd
import pytest

import backend.storage_access_layer.pipeline.utils.pipeline_utils as pipeline_utils
from backend.storage_access_layer.pipeline.utils.pipeline_utils import (
    _find_next_footstep,
    _get_angle_between,
    _get_footstep_row,
    _is_within_expect_duration,
    _is_within_expected_bb_size,
    get_heading,
    identify_anchor_footstep,
    load_metadata,
    parse_identifying_components_from_path,
    reset_path_order,
    trace_path,
)

pytestmark = pytest.mark.unit


def _make_footstep_metadata(rows):
    return pd.DataFrame(rows)


class TestPathMetadataHelpers:
    def test_parse_identifying_components_from_path_returns_expected_parts(self):
        path = pathlib.Path("12/2025-03-10/out/4/data.npy")

        participant, date, direction, swipe_n = parse_identifying_components_from_path(
            path
        )

        assert participant == 12
        assert date == "2025-03-10"
        assert direction == "out"
        assert swipe_n == 4

    def test_load_metadata_parses_timestamp_column(self, tmp_path):
        metadata_path = tmp_path / "metadata.csv"
        metadata_path.write_text(
            "Timestamp,FootstepID\n2025-03-10T12:34:56Z,7\n", encoding="utf-8"
        )

        metadata = load_metadata(metadata_path)
        timestamp = pd.Timestamp(str(metadata.loc[0, "Timestamp"]))

        assert metadata.loc[0, "FootstepID"] == 7
        assert timestamp.isoformat() == "2025-03-10T12:34:56+00:00"


class TestAnchorFootstep:
    def test_identify_anchor_footstep_prefers_expected_outbound_target(self):
        metadata = _make_footstep_metadata(
            [
                {
                    "FootstepID": 1,
                    "Direction": "out",
                    "Gate": 3,
                    "t": 25,
                    "x": 60,
                    "y": 10,
                    "path_order": -1,
                },
                {
                    "FootstepID": 2,
                    "Direction": "out",
                    "Gate": 3,
                    "t": 250,
                    "x": 160,
                    "y": 180,
                    "path_order": -1,
                },
            ]
        )

        identify_anchor_footstep(metadata)

        assert list(metadata["path_order"]) == [0, -1]

    def test_identify_anchor_footstep_prefers_inbound_step_near_3000ms(self):
        metadata = _make_footstep_metadata(
            [
                {
                    "FootstepID": 1,
                    "Direction": "in",
                    "Gate": 1,
                    "t": 3000,
                    "x": 220,
                    "y": 10,
                    "path_order": -1,
                },
                {
                    "FootstepID": 2,
                    "Direction": "in",
                    "Gate": 1,
                    "t": 2800,
                    "x": 260,
                    "y": 50,
                    "path_order": -1,
                },
            ]
        )

        identify_anchor_footstep(metadata)

        assert list(metadata["path_order"]) == [0, -1]


class TestGeometryHelpers:
    def test_get_heading_normalizes_negative_angles(self, monkeypatch):
        class DummyPCA:
            def __init__(self, n_components):
                assert n_components == 2
                self.components_ = np.array([[0.0, -1.0], [1.0, 0.0]])

            def fit(self, values):
                assert values.shape[1] == 2
                return self

        monkeypatch.setattr(pipeline_utils, "PCA", DummyPCA)

        row = pd.Series({"XMin": 1, "XMax": 4, "YMin": 2, "YMax": 6})
        trial_p100 = np.zeros((8, 8), dtype=int)
        trial_p100[2:6, 1:4] = 1

        heading = get_heading(row, trial_p100)

        assert heading == pytest.approx(0.0)

    @pytest.mark.parametrize(
        ("row", "expected"),
        [
            (pd.Series({"XMin": 0, "XMax": 30, "YMin": 0, "YMax": 60}), True),
            (pd.Series({"XMin": 0, "XMax": 10, "YMin": 0, "YMax": 60}), False),
            (pd.Series({"XMin": 0, "XMax": 30, "YMin": 0, "YMax": 120}), False),
        ],
    )
    def test_is_within_expected_bb_size(self, row, expected):
        assert bool(_is_within_expected_bb_size(row)) is expected

    @pytest.mark.parametrize(
        ("row", "expected"),
        [
            (pd.Series({"StartFrame": 0, "EndFrame": 120}), True),
            (pd.Series({"StartFrame": 0, "EndFrame": 50}), False),
            (pd.Series({"StartFrame": 0, "EndFrame": 400}), False),
        ],
    )
    def test_is_within_expect_duration(self, row, expected):
        assert bool(_is_within_expect_duration(row)) is expected

    def test_get_angle_between_wraps_negative_angles_into_zero_to_two_pi(self):
        footstep_a = pd.Series({"x": 0, "y": 0})
        footstep_b = pd.Series({"x": 0, "y": 10})

        angle = _get_angle_between(footstep_a, footstep_b)

        assert angle == pytest.approx(1.5 * np.pi)


class TestFootstepSelectionHelpers:
    def test_get_footstep_row_returns_first_matching_row(self):
        metadata = _make_footstep_metadata(
            [
                {"FootstepID": 10, "x": 10},
                {"FootstepID": 10, "x": 20},
                {"FootstepID": 11, "x": 30},
            ]
        )

        row = _get_footstep_row(metadata, 10)

        assert row is not None
        assert row["x"] == 10

    def test_get_footstep_row_returns_none_when_missing(self):
        metadata = _make_footstep_metadata([{"FootstepID": 10, "x": 10}])

        assert _get_footstep_row(metadata, 999) is None

    def test_find_next_footstep_returns_empty_for_unknown_current_step(self):
        metadata = _make_footstep_metadata([{"FootstepID": 1, "path_order": -1}])

        assert _find_next_footstep(metadata, 999) == {}

    def test_find_next_footstep_scores_only_valid_outbound_candidates(self):
        metadata = _make_footstep_metadata(
            [
                {
                    "FootstepID": 1,
                    "Direction": "out",
                    "t": 100,
                    "x": 100,
                    "y": 100,
                    "heading_angle": 0.0,
                    "path_order": 0,
                },
                {
                    "FootstepID": 2,
                    "Direction": "out",
                    "t": 150,
                    "x": 50,
                    "y": 100,
                    "heading_angle": 0.0,
                    "path_order": -1,
                },
                {
                    "FootstepID": 3,
                    "Direction": "out",
                    "t": 190,
                    "x": 40,
                    "y": 130,
                    "heading_angle": 0.0,
                    "path_order": -1,
                },
                {
                    "FootstepID": 4,
                    "Direction": "out",
                    "t": 105,
                    "x": 40,
                    "y": 100,
                    "heading_angle": 0.0,
                    "path_order": -1,
                },
                {
                    "FootstepID": 5,
                    "Direction": "out",
                    "t": 140,
                    "x": 400,
                    "y": 100,
                    "heading_angle": 0.0,
                    "path_order": -1,
                },
            ]
        )

        loss_dict = _find_next_footstep(metadata, 1)

        assert set(loss_dict) == {2, 3}
        assert loss_dict[2] < loss_dict[3]

    def test_find_next_footstep_uses_backward_time_window_for_inbound_steps(self):
        metadata = _make_footstep_metadata(
            [
                {
                    "FootstepID": 10,
                    "Direction": "in",
                    "t": 500,
                    "x": 200,
                    "y": 200,
                    "heading_angle": np.pi,
                    "path_order": 0,
                },
                {
                    "FootstepID": 11,
                    "Direction": "in",
                    "t": 430,
                    "x": 250,
                    "y": 200,
                    "heading_angle": np.pi,
                    "path_order": -1,
                },
                {
                    "FootstepID": 12,
                    "Direction": "in",
                    "t": 650,
                    "x": 250,
                    "y": 200,
                    "heading_angle": np.pi,
                    "path_order": -1,
                },
            ]
        )

        loss_dict = _find_next_footstep(metadata, 10)

        assert set(loss_dict) == {11}


class TestTracePath:
    def test_trace_path_returns_without_anchor(self, capsys):
        metadata = _make_footstep_metadata(
            [{"FootstepID": 1, "path_order": -1, "x": 0, "y": 0}]
        )

        trace_path(metadata)

        captured = capsys.readouterr()
        assert (
            captured.out.strip()
            == "No anchor footstep found. Path tracing cannot proceed."
        )

    def test_trace_path_assigns_path_order_until_no_candidates_remain(
        self, monkeypatch
    ):
        metadata = _make_footstep_metadata(
            [
                {
                    "FootstepID": 1,
                    "path_order": 0,
                    "x": 240,
                    "y": 360,
                    "heading_angle": 0.0,
                },
                {
                    "FootstepID": 2,
                    "path_order": -1,
                    "x": 260,
                    "y": 360,
                    "heading_angle": 0.0,
                },
                {
                    "FootstepID": 3,
                    "path_order": -1,
                    "x": 280,
                    "y": 360,
                    "heading_angle": 0.0,
                },
            ]
        )

        candidate_map = {
            1: {2: 0.05},
            2: {3: 0.05},
            3: {},
        }

        def fake_find_next_footstep(frame, current_footstep_id):
            return candidate_map[current_footstep_id]

        monkeypatch.setattr(
            pipeline_utils, "_find_next_footstep", fake_find_next_footstep
        )

        trace_path(metadata)

        assert list(metadata.sort_values("FootstepID")["path_order"]) == [0, 1, 2]


class TestResetPathOrder:
    @pytest.mark.parametrize(
        ("path_order", "expected"),
        [
            (0, 0),
            (3, -1),
            (-1, -1),
        ],
    )
    def test_reset_path_order_preserves_anchor_only(self, path_order, expected):
        row = pd.Series({"path_order": path_order})

        assert reset_path_order(row) == expected
