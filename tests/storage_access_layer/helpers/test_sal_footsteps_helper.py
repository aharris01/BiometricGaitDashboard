from __future__ import annotations

import datetime as dt
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pytest

import backend.storage_access_layer.helpers.sal_footsteps as sal_footsteps_module
from backend.storage_access_layer.helpers.sal_footsteps import SalFootsteps
from backend.storage_access_layer.utils.types import FootstepSearchFilters


def _write_npz_with_numeric_keys(path, arrays: dict[str, np.ndarray]) -> None:
    with ZipFile(path, mode="w", compression=ZIP_DEFLATED) as zf:
        for key, arr in arrays.items():
            buf = BytesIO()
            np.save(buf, arr)
            zf.writestr(f"{key}.npy", buf.getvalue())


@pytest.fixture
def fake_db():
    db = MagicMock()
    db.search_footsteps = MagicMock()
    db.get_event_footsteps = MagicMock()
    db.get_single_footstep = MagicMock()
    db.get_single_footstep.return_value = None
    db.get_local_footstep_changes = MagicMock(return_value=[])
    db.update_local_footstep = MagicMock()
    db.update_step_archive_keys = MagicMock()
    db.update_event_metrics = MagicMock()
    db.create_local_footstep = MagicMock()
    db.delete_local_footstep = MagicMock()
    return db


@pytest.fixture
def common():
    obj = MagicMock()
    obj._require_event = MagicMock(return_value=(SimpleNamespace(), None))
    obj._require_footstep = MagicMock(return_value=(SimpleNamespace(), None))
    obj._get_p100 = MagicMock(return_value=(np.array([[1.0, 2.0], [3.0, 4.0]]), None))
    obj._get_image_dims = MagicMock(return_value=(2, 2, None))
    obj._get_trial_frame_count = MagicMock(return_value=(20, None))
    obj._load_steps_npz = MagicMock()
    return obj


@pytest.fixture
def helper(fake_db, common):
    return SalFootsteps(fake_db, common)


class TestSearchFootstep:
    @pytest.mark.unit
    def test_search_footsteps_maps_rows(self, helper, fake_db):
        fake_db.search_footsteps.return_value = (
            [
                {
                    "event_id": "evt-1",
                    "footstep_id": 2,
                    "step_number": 7,
                    "participant": 11111,
                    "date": dt.date(2025, 1, 1),
                    "start_frame": 10,
                    "end_frame": 20,
                    "x_min": 5,
                    "x_max": 25,
                    "y_min": 7,
                    "y_max": 37,
                    "bbox_width": 20,
                    "bbox_height": 30,
                    "bbox_area": 600,
                }
            ],
            1,
        )
        search_params = FootstepSearchFilters(
            event_ids=["evt-1", ""], participants=[11111]
        )
        helper._check_footstep_data = MagicMock(return_value=True)
        out = helper.search_footsteps(search_params)
        assert out["total"] == 1
        assert out["items"][0]["date"] == "2025-01-01"
        assert out["items"][0]["step_number"] == 7


class TestGetFootstep:
    @pytest.mark.unit
    def test_get_footsteps_missing_event(self, helper, common):
        common._require_event.return_value = (None, "missing_event")
        steps, err = helper.get_footsteps("evt-1")
        assert steps is None
        assert err == "missing_event"

    @pytest.mark.unit
    def test_get_footstep_data_uses_step_archive_key(
        self, tmp_path, helper, common, fake_db
    ):
        trial = tmp_path / "trial.npz"
        np.savez(trial, arr_0=np.zeros((2, 2)))
        steps_path = trial.with_name("steps.npz")
        step_vol = np.array(
            [
                [[1.0, 2.0], [3.0, 4.0]],
                [[0.0, 1.0], [0.0, 0.0]],
            ]
        )
        _write_npz_with_numeric_keys(steps_path, {"9": step_vol})

        event = SimpleNamespace(trial_npz_uri=trial.as_uri())
        common._require_event.return_value = (event, None)
        common._load_steps_npz.return_value = (np.load(steps_path), None)
        fake_db.get_single_footstep.return_value = SimpleNamespace(step_archive_key=9)

        p100, grf, err = helper.get_footstep_data("evt-1", 4)

        assert err is None
        assert p100 == [[1.0, 2.0], [3.0, 4.0]]
        assert grf == [10.0, 1.0]

    @pytest.mark.unit
    def test_get_footstep_data_missing_key(self, tmp_path, helper, common):
        trial = tmp_path / "trial.npz"
        np.savez(trial, arr_0=np.zeros((2, 2)))
        steps_path = trial.with_name("steps.npz")
        _write_npz_with_numeric_keys(steps_path, {"1": np.ones((2, 2, 2))})

        event = SimpleNamespace(trial_npz_uri=trial.as_uri())
        common._require_event.return_value = (event, None)
        common._load_steps_npz.return_value = (np.load(steps_path), None)

        p100, grf, err = helper.get_footstep_data("evt-1", 0)
        assert p100 is None and grf is None
        assert err == "missing_file"

    @pytest.mark.unit
    def test_get_footstep_context_data_includes_cop(self, tmp_path, helper, common):
        trial = tmp_path / "trial.npz"
        np.savez(trial, arr_0=np.zeros((2, 2)))
        steps_path = trial.with_name("steps.npz")
        step_vol = np.array(
            [
                [[1.0, 0.0], [0.0, 0.0]],
                [[0.0, 0.0], [0.0, 2.0]],
            ]
        )
        _write_npz_with_numeric_keys(steps_path, {"0": step_vol})

        event = SimpleNamespace(trial_npz_uri=trial.as_uri())
        common._require_event.return_value = (event, None)
        common._load_steps_npz.return_value = (np.load(steps_path), None)

        details, err = helper.get_footstep_context_data("evt-1", 0)

        assert err is None
        assert details["p100"] == [[1.0, 0.0], [0.0, 2.0]]
        assert details["grf"] == [1.0, 2.0]
        assert details["cop_x"] == [0.0, 1.0]
        assert details["cop_y"] == [0.0, 1.0]

    @pytest.mark.unit
    def test_get_all_footstep_p100_maps_archive_keys_back_to_db_ids(
        self, tmp_path, helper, common, fake_db
    ):
        trial = tmp_path / "trial.npz"
        np.savez(trial, arr_0=np.zeros((2, 2)))
        steps_path = trial.with_name("steps.npz")
        _write_npz_with_numeric_keys(
            steps_path,
            {
                "3": np.ones((2, 2, 2)),
                "7": np.full((2, 2, 2), 2.0),
            },
        )

        event = SimpleNamespace(trial_npz_uri=trial.as_uri())
        common._require_event.return_value = (event, None)
        common._load_steps_npz.return_value = (np.load(steps_path), None)
        fake_db.get_event_footsteps.return_value = [
            {"footstep_id": 20, "step_archive_key": 7},
            {"footstep_id": 10, "step_archive_key": 3},
        ]

        items, err = helper.get_all_footstep_p100("evt-1")

        assert err is None
        assert items == [
            {"id": 10, "p100": [[1.0, 1.0], [1.0, 1.0]]},
            {"id": 20, "p100": [[2.0, 2.0], [2.0, 2.0]]},
        ]


class TestCreateDraftFootstep:
    @pytest.mark.unit
    def test_create_draft_footstep_returns_serialized_volume(self, helper, common):
        event = SimpleNamespace()
        common._require_event.return_value = (event, None)
        common._get_p100.return_value = (np.ones((8, 8), dtype=float), None)
        common._get_image_dims.return_value = (8, 8, None)
        helper.editor.create_draft_footstep = MagicMock(
            return_value=(
                {
                    "StartFrame": 12,
                    "EndFrame": 40,
                    "XMin": 1,
                    "XMax": 5,
                    "YMin": 2,
                    "YMax": 6,
                    "time_recording": np.ones((28, 4, 4), dtype=float),
                },
                None,
            )
        )

        out, err = helper.create_draft_footstep(
            "evt-1",
            {
                "x_min": 1,
                "x_max": 5,
                "y_min": 2,
                "y_max": 6,
            },
        )

        assert err is None
        assert out is not None
        assert out["event_id"] == "evt-1"
        assert out["start_frame"] == 12
        assert out["end_frame"] == 40
        assert out["depth"] == 28
        assert len(out["volume"]) == 28
        helper.editor.create_draft_footstep.assert_called_once()

    @pytest.mark.unit
    def test_create_draft_footstep_propagates_editor_error(self, helper, common):
        event = SimpleNamespace()
        common._require_event.return_value = (event, None)
        common._get_p100.return_value = (np.ones((8, 8), dtype=float), None)
        common._get_image_dims.return_value = (8, 8, None)
        helper.editor.create_draft_footstep = MagicMock(
            return_value=(None, "no_pressure_data")
        )

        out, err = helper.create_draft_footstep(
            "evt-1",
            {
                "x_min": 1,
                "x_max": 5,
                "y_min": 2,
                "y_max": 6,
            },
        )

        assert out is None
        assert err == "no_pressure_data"


class TestSaveFootstepReview:
    def _valid_edits(self):
        return {
            "x_min": 0,
            "x_max": 2,
            "y_min": 0,
            "y_max": 2,
            "start_frame": 1,
            "end_frame": 5,
            "label": " left ",
        }

    def _valid_review(self):
        return {"event_p100": [[1.0, 2.0], [3.0, 4.0]]}

    @pytest.mark.unit
    def test_save_footstep_review_missing_event_returns_error(self, helper, common):
        common._require_event.return_value = (None, "missing_event")

        out, err = helper.save_footstep_review("evt-1", 6, self._valid_edits())

        assert out is None
        assert err == "missing_event"

    @pytest.mark.unit
    def test_save_footstep_review_missing_p100_returns_error(self, helper, common):
        common._get_p100.return_value = (None, "missing_p100")

        out, err = helper.save_footstep_review("evt-1", 6, self._valid_edits())

        assert out is None
        assert err == "missing_p100"

    @pytest.mark.unit
    def test_save_footstep_review_invalid_bbox_returns_error(self, helper, fake_db):
        helper.editor.edit_footstep = MagicMock()

        edits = self._valid_edits()
        edits["x_min"] = -1

        out, err = helper.save_footstep_review("evt-1", 6, edits)

        assert out is None
        assert err == "invalid_bbox"
        helper.editor.edit_footstep.assert_not_called()
        fake_db.update_local_footstep.assert_not_called()
        fake_db.update_event_metrics.assert_not_called()

    @pytest.mark.unit
    def test_save_footstep_review_validator_dependency_error_is_propagated(
        self, helper, common, fake_db
    ):
        helper.get_footstep_review_context = MagicMock(
            return_value=(self._valid_review(), None)
        )
        helper.editor.edit_footstep = MagicMock()
        common._get_image_dims.return_value = (None, None, "bad_image")

        out, err = helper.save_footstep_review("evt-1", 6, self._valid_edits())

        assert out is None
        assert err == "bad_image"
        helper.editor.edit_footstep.assert_not_called()
        fake_db.update_local_footstep.assert_not_called()

    @pytest.mark.unit
    def test_save_footstep_review_editor_error_is_propagated(self, helper, fake_db):
        helper.get_footstep_review_context = MagicMock(
            return_value=(self._valid_review(), None)
        )
        helper.editor.edit_footstep = MagicMock(return_value=(False, "edit_error"))

        out, err = helper.save_footstep_review("evt-1", 6, self._valid_edits())

        assert out is None
        assert err == "edit_error"
        fake_db.update_local_footstep.assert_not_called()
        fake_db.update_event_metrics.assert_not_called()

    @pytest.mark.unit
    def test_save_footstep_review_editor_failure_without_error_returns_edit_failed(
        self, helper, fake_db
    ):
        helper.get_footstep_review_context = MagicMock(
            return_value=(self._valid_review(), None)
        )
        helper.editor.edit_footstep = MagicMock(return_value=(False, None))

        out, err = helper.save_footstep_review("evt-1", 6, self._valid_edits())

        assert out is None
        assert err == "edit_failed"
        fake_db.update_local_footstep.assert_not_called()

    @pytest.mark.unit
    def test_save_footstep_review_invalid_change_returns_error(self, helper, fake_db):
        helper.get_footstep_review_context = MagicMock(
            return_value=(self._valid_review(), None)
        )
        helper.editor.edit_footstep = MagicMock(return_value=(True, None))
        fake_db.update_local_footstep.side_effect = ValueError("bad_column")

        out, err = helper.save_footstep_review("evt-1", 6, self._valid_edits())

        assert out is None
        assert err == "invalid_change"
        fake_db.update_event_metrics.assert_not_called()

    @pytest.mark.unit
    def test_save_footstep_review_missing_db_footstep_returns_no_footstep(
        self, helper, fake_db
    ):
        helper.get_footstep_review_context = MagicMock(
            return_value=(self._valid_review(), None)
        )
        helper.editor.edit_footstep = MagicMock(return_value=(True, None))
        fake_db.update_local_footstep.return_value = None

        out, err = helper.save_footstep_review("evt-1", 6, self._valid_edits())

        assert out is None
        assert err == "no_footstep"
        fake_db.update_event_metrics.assert_not_called()

    @pytest.mark.unit
    def test_save_footstep_review_metrics_calculation_failure_returns_error(
        self, tmp_path, helper, common, fake_db, monkeypatch
    ):
        event = SimpleNamespace(trial_npz_uri=(tmp_path / "trial.npz").as_uri())
        common._require_event.return_value = (event, None)
        helper.get_footstep_review_context = MagicMock(
            return_value=(self._valid_review(), None)
        )
        helper.editor.edit_footstep = MagicMock(return_value=(True, None))
        fake_db.update_local_footstep.return_value = object()
        monkeypatch.setattr(
            sal_footsteps_module,
            "calculate_all_metrics",
            MagicMock(return_value=(None, "calc_failed")),
        )

        out, err = helper.save_footstep_review("evt-1", 6, self._valid_edits())

        assert out is None
        assert err == "calculation_error"
        fake_db.update_event_metrics.assert_not_called()

    @pytest.mark.unit
    def test_save_footstep_review_metrics_update_failure_returns_unexpected_error(
        self, tmp_path, helper, common, fake_db, monkeypatch
    ):
        event = SimpleNamespace(trial_npz_uri=(tmp_path / "trial.npz").as_uri())
        common._require_event.return_value = (event, None)
        helper.get_footstep_review_context = MagicMock(
            side_effect=[(self._valid_review(), None), ({"saved": True}, None)]
        )
        helper.editor.edit_footstep = MagicMock(return_value=(True, None))
        fake_db.update_local_footstep.return_value = object()
        fake_db.update_event_metrics.return_value = None
        calc_metrics = MagicMock(return_value=({"step_count": 4}, None))
        monkeypatch.setattr(sal_footsteps_module, "calculate_all_metrics", calc_metrics)

        out, err = helper.save_footstep_review("evt-1", 6, self._valid_edits())

        assert out is None
        assert err == "unexpected_error"
        calc_metrics.assert_called_once_with("evt-1", tmp_path / "metadata.csv")

    @pytest.mark.unit
    def test_save_footstep_review_success_normalizes_label_and_returns_refreshed_review(
        self, tmp_path, helper, common, fake_db, monkeypatch
    ):
        event = SimpleNamespace(trial_npz_uri=(tmp_path / "trial.npz").as_uri())
        common._require_event.return_value = (event, None)
        helper.editor.edit_footstep = MagicMock(return_value=(True, None))
        fake_db.update_local_footstep.return_value = SimpleNamespace(
            event_id="evt-1",
            footstep_id=6,
            start_frame=1,
            x_min=0,
            x_max=2,
            y_min=0,
            y_max=2,
            end_frame=5,
            label="left",
        )
        fake_db.update_event_metrics.return_value = object()
        calc_metrics = MagicMock(return_value=({"step_count": 4}, None))
        monkeypatch.setattr(sal_footsteps_module, "calculate_all_metrics", calc_metrics)
        edits = self._valid_edits()

        out, err = helper.save_footstep_review("evt-1", 6, edits)

        assert err is None
        assert out == {
            "item": {
                "event_id": "evt-1",
                "footstep_id": 6,
                "start_frame": 1,
                "end_frame": 5,
                "label": "left",
            },
            "bbox": {
                "x_min": 0,
                "x_max": 2,
                "y_min": 0,
                "y_max": 2,
            },
            "event_p100": [[1.0, 2.0], [3.0, 4.0]],
            "changes": [],
        }
        assert out["item"]["label"] == "left"
        fake_db.update_local_footstep.assert_called_once_with("evt-1", 6, edits)
        calc_metrics.assert_called_once_with("evt-1", tmp_path / "metadata.csv")
        fake_db.update_event_metrics.assert_called_once_with("evt-1", {"step_count": 4})

    @pytest.mark.unit
    def test_save_footstep_review_blank_label_becomes_none(
        self, tmp_path, helper, common, fake_db, monkeypatch
    ):
        event = SimpleNamespace(trial_npz_uri=(tmp_path / "trial.npz").as_uri())
        common._require_event.return_value = (event, None)
        helper.get_footstep_review_context = MagicMock(
            side_effect=[(self._valid_review(), None), ({"saved": True}, None)]
        )
        helper.editor.edit_footstep = MagicMock(return_value=(True, None))
        fake_db.update_local_footstep.return_value = SimpleNamespace(
            event_id="evt-1",
            footstep_id=6,
            start_frame=1,
            x_min=0,
            x_max=2,
            y_min=0,
            y_max=2,
            end_frame=5,
            label=None,
        )
        fake_db.update_event_metrics.return_value = object()
        monkeypatch.setattr(
            sal_footsteps_module,
            "calculate_all_metrics",
            MagicMock(return_value=({"step_count": 4}, None)),
        )
        edits = self._valid_edits()
        edits["label"] = "   "

        out, err = helper.save_footstep_review("evt-1", 6, edits)

        assert err is None
        assert out == {
            "item": {
                "event_id": "evt-1",
                "footstep_id": 6,
                "start_frame": 1,
                "end_frame": 5,
                "label": None,
            },
            "bbox": {
                "x_min": 0,
                "x_max": 2,
                "y_min": 0,
                "y_max": 2,
            },
            "event_p100": [[1.0, 2.0], [3.0, 4.0]],
            "changes": [],
        }
        assert edits["label"] is None


class TestCreateFootstep:
    @pytest.mark.unit
    def test_create_footstep_without_label_uses_none(self, helper, common, fake_db):
        event = SimpleNamespace()
        common._require_event.return_value = (event, None)
        common._get_p100.return_value = (np.array([[1.0, 2.0], [3.0, 4.0]]), None)
        common._get_trial_frame_count.return_value = (20, None)
        helper.editor.create_footstep = MagicMock(return_value=(9, None))
        fake_db.create_local_footstep.return_value = SimpleNamespace(
            footstep_id=9,
            **{
                "start_frame": 1,
                "end_frame": 5,
                "x_min": 0,
                "x_max": 2,
                "y_min": 0,
                "y_max": 2,
                "label": None,
            },
        )

        out, err = helper.create_footstep(
            "evt-1",
            {
                "start_frame": 1,
                "end_frame": 5,
                "x_min": 0,
                "x_max": 2,
                "y_min": 0,
                "y_max": 2,
                "label": None,
            },
        )

        assert err is None
        assert out == {
            "item": {
                "event_id": "evt-1",
                "footstep_id": 9,
                "start_frame": 1,
                "end_frame": 5,
                "label": None,
            },
            "bbox": {
                "x_min": 0,
                "x_max": 2,
                "y_min": 0,
                "y_max": 2,
            },
            "event_p100": [[1.0, 2.0], [3.0, 4.0]],
            "changes": [],
        }
        fake_db.create_local_footstep.assert_called_once_with(
            "evt-1",
            step_archive_key=9,
            start_frame=1,
            end_frame=5,
            x_min=0,
            x_max=2,
            y_min=0,
            y_max=2,
            label=None,
        )
        helper.editor.create_footstep.assert_called_once_with(
            "evt-1",
            {
                "start_frame": 1,
                "end_frame": 5,
                "x_min": 0,
                "x_max": 2,
                "y_min": 0,
                "y_max": 2,
            },
        )

    @pytest.mark.unit
    def test_create_footstep_propagates_pipeline_editor_error(
        self, helper, common, fake_db
    ):
        event = SimpleNamespace()
        common._require_event.return_value = (event, None)
        common._get_p100.return_value = (np.array([[1.0, 2.0], [3.0, 4.0]]), None)
        common._get_trial_frame_count.return_value = (20, None)
        helper.editor.create_footstep = MagicMock(return_value=(False, "missing_file"))

        out, err = helper.create_footstep(
            "evt-1",
            {
                "start_frame": 1,
                "end_frame": 5,
                "x_min": 0,
                "x_max": 2,
                "y_min": 0,
                "y_max": 2,
                "label": None,
            },
        )

        assert out is None
        assert err == "missing_file"
        fake_db.create_local_footstep.assert_not_called()

    @pytest.mark.unit
    def test_create_footstep_updates_existing_archive_keys_before_insert(
        self, helper, common, fake_db
    ):
        event = SimpleNamespace()
        common._require_event.return_value = (event, None)
        common._get_p100.return_value = (np.array([[1.0, 2.0], [3.0, 4.0]]), None)
        common._get_trial_frame_count.return_value = (20, None)
        helper.editor.create_footstep = MagicMock(
            return_value=(
                {
                    "step_archive_key": 2,
                    "archive_key_updates": {0: 0, 1: 3},
                },
                None,
            )
        )
        fake_db.create_local_footstep.return_value = SimpleNamespace(
            footstep_id=9,
            start_frame=1,
            end_frame=5,
            x_min=0,
            x_max=2,
            y_min=0,
            y_max=2,
            label=None,
        )

        out, err = helper.create_footstep(
            "evt-1",
            {
                "start_frame": 1,
                "end_frame": 5,
                "x_min": 0,
                "x_max": 2,
                "y_min": 0,
                "y_max": 2,
                "label": None,
            },
        )

        assert err is None
        assert out is not None
        fake_db.update_step_archive_keys.assert_called_once_with("evt-1", {0: 0, 1: 3})
        fake_db.create_local_footstep.assert_called_once_with(
            "evt-1",
            step_archive_key=2,
            start_frame=1,
            end_frame=5,
            x_min=0,
            x_max=2,
            y_min=0,
            y_max=2,
            label=None,
        )
