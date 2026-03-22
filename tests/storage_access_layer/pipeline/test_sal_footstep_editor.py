from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest
from flask import Flask

import backend.storage_access_layer.pipeline.footstep_edits as footstep_edits
from backend.storage_access_layer.pipeline.footstep_edits import (
    FootstepEditor,
    _update_csv,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def flask_app():
    return Flask(__name__)


@pytest.fixture
def common():
    return MagicMock()


@pytest.fixture
def editor(common):
    return FootstepEditor(db=MagicMock(), common=common)


@pytest.fixture
def event(tmp_path):
    trial_path = tmp_path / "trial.npz"
    return SimpleNamespace(
        event_id="event-1",
        trial_npz_uri=trial_path.as_uri(),
        trial_p100_npz_uri=(tmp_path / "p100.npz").as_uri(),
    )


def _make_metadata():
    return pd.DataFrame(
        [
            {
                "FootstepID": 7,
                "XMin": 5,
                "XMax": 35,
                "YMin": 10,
                "YMax": 70,
                "StartFrame": 20,
                "EndFrame": 140,
                "valid": True,
                "Direction": "out",
                "Gate": 3,
                "t": 25,
                "x": 60,
                "y": 10,
            }
        ]
    )


def _make_delete_metadata():
    return pd.DataFrame(
        [
            {
                "FootstepID": 6,
                "XMin": 2,
                "XMax": 22,
                "YMin": 6,
                "YMax": 36,
                "StartFrame": 10,
                "EndFrame": 90,
                "valid": True,
                "Direction": "out",
                "Gate": 3,
                "t": 10,
                "x": 40,
                "y": 10,
            },
            {
                "FootstepID": 7,
                "XMin": 5,
                "XMax": 35,
                "YMin": 10,
                "YMax": 70,
                "StartFrame": 20,
                "EndFrame": 140,
                "valid": True,
                "Direction": "out",
                "Gate": 3,
                "t": 25,
                "x": 60,
                "y": 10,
            },
        ]
    )


def _make_new_footstep_data():
    return {
        "XMin": 12,
        "XMax": 44,
        "YMin": 18,
        "YMax": 82,
        "StartFrame": 30,
        "EndFrame": 190,
    }


def _write_step_archives(trial_dir, step_ids):
    for filename in ("steps.npz", "steps.raw.npz"):
        archive_path = trial_dir / filename
        with ZipFile(archive_path, "w") as archive:
            for step_id in step_ids:
                archive.writestr(f"{step_id}.npy", b"stub")


def _make_create_metadata():
    return pd.DataFrame(
        [
            {
                "FootstepID": 0,
                "XMin": 2,
                "XMax": 22,
                "YMin": 6,
                "YMax": 36,
                "StartFrame": 10,
                "EndFrame": 90,
                "valid": True,
                "Direction": "out",
                "Gate": 3,
                "t": 10,
                "x": 12,
                "y": 21,
            },
            {
                "FootstepID": 1,
                "XMin": 5,
                "XMax": 35,
                "YMin": 10,
                "YMax": 70,
                "StartFrame": 20,
                "EndFrame": 140,
                "valid": True,
                "Direction": "out",
                "Gate": 3,
                "t": 25,
                "x": 20,
                "y": 40,
            },
            {
                "FootstepID": 2,
                "XMin": 8,
                "XMax": 28,
                "YMin": 12,
                "YMax": 42,
                "StartFrame": 30,
                "EndFrame": 160,
                "valid": True,
                "Direction": "out",
                "Gate": 3,
                "t": 35,
                "x": 18,
                "y": 27,
            },
        ]
    )


class TestFootstepEditorFailures:
    def test_edit_footstep_returns_event_error_when_event_lookup_fails(
        self, editor, common
    ):
        common._require_event.return_value = (None, "missing_event")

        ok, err = editor.edit_footstep(7, "event-1", _make_new_footstep_data(), p100=[])

        assert ok is False
        assert err == "missing_event"
        common._require_footstep.assert_not_called()

    def test_edit_footstep_returns_footstep_error_when_lookup_fails(
        self, editor, common, event
    ):
        common._require_event.return_value = (event, None)
        common._require_footstep.return_value = (None, "missing_footstep")

        ok, err = editor.edit_footstep(7, "event-1", _make_new_footstep_data(), p100=[])

        assert ok is False
        assert err == "missing_footstep"

    def test_edit_footstep_returns_error_when_metadata_load_fails(
        self, flask_app, editor, common, event, monkeypatch
    ):
        common._require_event.return_value = (event, None)
        common._require_footstep.return_value = (object(), None)
        monkeypatch.setattr(
            footstep_edits,
            "load_metadata",
            MagicMock(side_effect=RuntimeError("metadata blew up")),
        )

        with flask_app.app_context():
            ok, err = editor.edit_footstep(7, "event-1", _make_new_footstep_data(), [])

        assert ok is False
        assert err == "Error loading metadata: metadata blew up"

    def test_edit_footstep_returns_trial_recording_error_when_load_fails(
        self, flask_app, editor, common, event, monkeypatch
    ):
        common._require_event.return_value = (event, None)
        common._require_footstep.return_value = (object(), None)
        monkeypatch.setattr(
            footstep_edits, "load_metadata", MagicMock(return_value=_make_metadata())
        )
        monkeypatch.setattr(
            footstep_edits, "identify_anchor_footstep", lambda metadata: None
        )
        monkeypatch.setattr(footstep_edits, "get_heading", lambda row, p100: 0.0)
        monkeypatch.setattr(footstep_edits, "reset_path_order", lambda row: -1)
        monkeypatch.setattr(footstep_edits, "trace_path", lambda metadata: None)
        common._load_trial_recording.return_value = (None, "trial_load_failed")

        with flask_app.app_context():
            ok, err = editor.edit_footstep(
                7,
                "event-1",
                _make_new_footstep_data(),
                p100=np.ones((120, 120), dtype=float),
            )

        assert ok is False
        assert err == "trial_load_failed"


class TestFootstepEditorSuccessPaths:
    def test_edit_footstep_updates_metadata_and_saves_outputs(
        self, flask_app, editor, common, event, monkeypatch
    ):
        metadata = _make_metadata()
        new_footstep_data = _make_new_footstep_data()
        updated_metadata = metadata.copy()
        for key, value in new_footstep_data.items():
            updated_metadata.loc[updated_metadata["FootstepID"] == 7, key] = value
        updated_metadata["valid"] = True
        updated_metadata["heading_angle"] = 1.25
        updated_metadata["path_order"] = 0
        updated_metadata["is_anchor"] = True
        updated_metadata["is_on_path"] = True
        load_metadata_mock = MagicMock(return_value=metadata.copy())
        update_csv_mock = MagicMock(return_value=(True, None))
        preprocess_mock = MagicMock(
            return_value=(
                np.full((1, 101, 100, 100), 3, dtype=np.uint16),
                updated_metadata,
            )
        )
        trial_recording = np.arange(250 * 120 * 120).reshape(250, 120, 120)
        trial_dir = footstep_edits.uri_to_path(event.trial_npz_uri).parent
        _write_step_archives(trial_dir, (7,))

        common._require_event.return_value = (event, None)
        common._require_footstep.return_value = (object(), None)
        common._load_trial_recording.return_value = (trial_recording, None)

        monkeypatch.setattr(footstep_edits, "load_metadata", load_metadata_mock)
        monkeypatch.setattr(
            footstep_edits, "_is_within_expected_bb_size", lambda row: True
        )
        monkeypatch.setattr(
            footstep_edits, "_is_within_expect_duration", lambda row: True
        )
        monkeypatch.setattr(
            footstep_edits, "identify_anchor_footstep", lambda metadata: None
        )
        monkeypatch.setattr(footstep_edits, "get_heading", lambda row, p100: 1.25)
        monkeypatch.setattr(footstep_edits, "reset_path_order", lambda row: 0)
        monkeypatch.setattr(footstep_edits, "trace_path", lambda metadata: None)
        monkeypatch.setattr(footstep_edits, "preprocess_footsteps", preprocess_mock)
        monkeypatch.setattr(footstep_edits, "_update_csv", update_csv_mock)

        with flask_app.app_context():
            ok, err = editor.edit_footstep(
                7,
                "event-1",
                new_footstep_data,
                p100=np.ones((120, 120), dtype=float),
            )

        assert ok is True
        assert err is None
        edited_metadata = update_csv_mock.call_args.args[0]
        edited_row = edited_metadata.loc[edited_metadata["FootstepID"] == 7].iloc[0]
        for key, value in new_footstep_data.items():
            assert edited_row[key] == value
        assert bool(edited_row["valid"]) is True
        assert bool(edited_row["is_anchor"]) is True
        assert bool(edited_row["is_on_path"]) is True
        assert edited_row["heading_angle"] == 1.25

        preprocess_footsteps_arg = preprocess_mock.call_args.args[0]
        assert preprocess_footsteps_arg[7].shape == (160, 64, 32)
        with ZipFile(trial_dir / "steps.npz") as archive:
            assert sorted(archive.namelist()) == ["7.npy"]
            processed_member = np.load(BytesIO(archive.read("7.npy")))
            assert processed_member.shape == (101, 100, 100)
        with ZipFile(trial_dir / "steps.raw.npz") as archive:
            assert sorted(archive.namelist()) == ["7.npy"]

    def test_edit_footstep_saves_single_processed_step_without_batch_dimension(
        self, flask_app, editor, common, event, monkeypatch
    ):
        metadata = _make_metadata()
        processed_batch = np.full((1, 101, 100, 100), 7, dtype=np.uint16)
        trial_recording = np.arange(250 * 120 * 120).reshape(250, 120, 120)
        trial_dir = footstep_edits.uri_to_path(event.trial_npz_uri).parent
        _write_step_archives(trial_dir, (7,))

        common._require_event.return_value = (event, None)
        common._require_footstep.return_value = (object(), None)
        common._load_trial_recording.return_value = (trial_recording, None)

        monkeypatch.setattr(
            footstep_edits, "load_metadata", MagicMock(return_value=metadata.copy())
        )
        monkeypatch.setattr(
            footstep_edits, "_is_within_expected_bb_size", lambda row: True
        )
        monkeypatch.setattr(
            footstep_edits, "_is_within_expect_duration", lambda row: True
        )
        monkeypatch.setattr(
            footstep_edits, "identify_anchor_footstep", lambda metadata: None
        )
        monkeypatch.setattr(footstep_edits, "get_heading", lambda row, p100: 0.0)
        monkeypatch.setattr(footstep_edits, "reset_path_order", lambda row: -1)
        monkeypatch.setattr(footstep_edits, "trace_path", lambda metadata: None)
        monkeypatch.setattr(
            footstep_edits,
            "preprocess_footsteps",
            MagicMock(return_value=(processed_batch, metadata.copy())),
        )
        monkeypatch.setattr(
            footstep_edits, "_update_csv", MagicMock(return_value=(True, None))
        )

        with flask_app.app_context():
            ok, err = editor.edit_footstep(
                7,
                "event-1",
                _make_new_footstep_data(),
                p100=np.ones((120, 120), dtype=float),
            )

        assert ok is True
        assert err is None
        with ZipFile(trial_dir / "steps.npz") as archive:
            processed_member = np.load(BytesIO(archive.read("7.npy")))
        assert processed_member.shape == (101, 100, 100)
        np.testing.assert_array_equal(processed_member, processed_batch[0])

    def test_edit_footstep_marks_step_invalid_when_edited_bounds_fail_validation(
        self, flask_app, editor, common, event, monkeypatch
    ):
        metadata = _make_metadata()
        updated_metadata = metadata.copy()
        for key, value in _make_new_footstep_data().items():
            updated_metadata.loc[updated_metadata["FootstepID"] == 7, key] = value
        updated_metadata["valid"] = False
        update_csv_mock = MagicMock(return_value=(True, None))
        trial_dir = footstep_edits.uri_to_path(event.trial_npz_uri).parent
        _write_step_archives(trial_dir, (7,))

        common._require_event.return_value = (event, None)
        common._require_footstep.return_value = (object(), None)
        common._load_trial_recording.return_value = (
            np.zeros((250, 120, 120), dtype=float),
            None,
        )

        monkeypatch.setattr(
            footstep_edits, "load_metadata", MagicMock(return_value=metadata)
        )
        monkeypatch.setattr(
            footstep_edits, "_is_within_expected_bb_size", lambda row: False
        )
        monkeypatch.setattr(
            footstep_edits, "_is_within_expect_duration", lambda row: True
        )
        monkeypatch.setattr(
            footstep_edits, "identify_anchor_footstep", lambda metadata: None
        )
        monkeypatch.setattr(footstep_edits, "get_heading", lambda row, p100: 0.0)
        monkeypatch.setattr(footstep_edits, "reset_path_order", lambda row: -1)
        monkeypatch.setattr(footstep_edits, "trace_path", lambda metadata: None)
        monkeypatch.setattr(
            footstep_edits,
            "preprocess_footsteps",
            MagicMock(
                return_value=(
                    np.zeros((1, 101, 100, 100), dtype=np.uint16),
                    updated_metadata,
                )
            ),
        )
        monkeypatch.setattr(footstep_edits, "_update_csv", update_csv_mock)

        with flask_app.app_context():
            ok, err = editor.edit_footstep(
                7,
                "event-1",
                _make_new_footstep_data(),
                p100=np.zeros((720, 480)),
            )

        assert ok is True
        assert err is None
        edited_metadata = update_csv_mock.call_args.args[0]
        edited_row = edited_metadata.loc[edited_metadata["FootstepID"] == 7].iloc[0]
        assert bool(edited_row["valid"]) is False

    def test_edit_footstep_returns_error_when_saving_steps_file_fails(
        self, flask_app, editor, common, event, monkeypatch
    ):
        trial_dir = footstep_edits.uri_to_path(event.trial_npz_uri).parent
        _write_step_archives(trial_dir, (7,))

        common._require_event.return_value = (event, None)
        common._require_footstep.return_value = (object(), None)
        common._load_trial_recording.return_value = (
            np.zeros((250, 120, 120), dtype=float),
            None,
        )

        monkeypatch.setattr(
            footstep_edits, "load_metadata", MagicMock(return_value=_make_metadata())
        )
        monkeypatch.setattr(
            footstep_edits, "_is_within_expected_bb_size", lambda row: True
        )
        monkeypatch.setattr(
            footstep_edits, "_is_within_expect_duration", lambda row: True
        )
        monkeypatch.setattr(
            footstep_edits, "identify_anchor_footstep", lambda metadata: None
        )
        monkeypatch.setattr(footstep_edits, "get_heading", lambda row, p100: 0.0)
        monkeypatch.setattr(footstep_edits, "reset_path_order", lambda row: -1)
        monkeypatch.setattr(footstep_edits, "trace_path", lambda metadata: None)
        monkeypatch.setattr(
            footstep_edits,
            "preprocess_footsteps",
            MagicMock(
                return_value=(
                    np.zeros((1, 101, 100, 100), dtype=np.uint16),
                    _make_metadata(),
                )
            ),
        )
        monkeypatch.setattr(
            footstep_edits,
            "_rewrite_npz_member",
            MagicMock(side_effect=OSError("disk full")),
        )

        with flask_app.app_context():
            with pytest.raises(OSError, match="disk full"):
                editor.edit_footstep(7, "event-1", _make_new_footstep_data(), p100=[])

    def test_delete_footstep_updates_metadata_and_saves_outputs(
        self, flask_app, editor, common, event, monkeypatch
    ):
        metadata = _make_delete_metadata()
        footstep = SimpleNamespace(footstep_id=7)
        load_metadata_mock = MagicMock(return_value=metadata.copy())
        update_csv_mock = MagicMock(return_value=(True, None))
        trial_dir = footstep_edits.uri_to_path(event.trial_npz_uri).parent
        _write_step_archives(trial_dir, (6, 7))

        common._require_event.return_value = (event, None)
        common._require_footstep.return_value = (object(), None)
        common._load_npz_from_uri.return_value = (
            np.ones((120, 120), dtype=float),
            None,
        )

        monkeypatch.setattr(footstep_edits, "load_metadata", load_metadata_mock)
        monkeypatch.setattr(
            footstep_edits, "identify_anchor_footstep", lambda metadata: None
        )
        monkeypatch.setattr(footstep_edits, "get_heading", lambda row, p100: 2.5)
        monkeypatch.setattr(footstep_edits, "reset_path_order", lambda row: 0)
        monkeypatch.setattr(footstep_edits, "trace_path", lambda metadata: None)
        monkeypatch.setattr(footstep_edits, "_update_csv", update_csv_mock)

        with flask_app.app_context():
            ok, err = editor.delete_footstep(footstep, event)

        assert ok is True
        assert err is None

        updated_metadata = update_csv_mock.call_args.args[0]
        assert list(updated_metadata["FootstepID"]) == [6]
        assert bool(updated_metadata.iloc[0]["is_anchor"]) is True
        assert bool(updated_metadata.iloc[0]["is_on_path"]) is True
        assert updated_metadata.iloc[0]["heading_angle"] == 2.5
        with ZipFile(trial_dir / "steps.npz") as archive:
            assert sorted(archive.namelist()) == ["6.npy"]
        with ZipFile(trial_dir / "steps.raw.npz") as archive:
            assert sorted(archive.namelist()) == ["6.npy"]

    def test_create_draft_footstep_returns_active_time_window_and_bbox(
        self, flask_app, editor, common, event
    ):
        trial_recording = np.zeros((120, 80, 90), dtype=float)
        trial_recording[30:61, 10:30, 5:25] = 1.0

        common._require_event.return_value = (event, None)
        common._load_trial_recording.return_value = (trial_recording, None)

        with flask_app.app_context():
            draft, err = editor.create_draft_footstep(
                "event-1",
                {
                    "x_min": 5,
                    "x_max": 25,
                    "y_min": 10,
                    "y_max": 30,
                },
            )

        assert err is None
        assert draft is not None
        assert draft["StartFrame"] == 10
        assert draft["EndFrame"] == 81
        assert draft["XMin"] == 5
        assert draft["XMax"] == 25
        assert draft["YMin"] == 10
        assert draft["YMax"] == 30
        np.testing.assert_array_equal(
            draft["time_recording"],
            trial_recording[10:81, 10:30, 5:25],
        )

    def test_create_draft_footstep_returns_error_when_bbox_has_no_pressure(
        self, flask_app, editor, common, event
    ):
        common._require_event.return_value = (event, None)
        common._load_trial_recording.return_value = (
            np.zeros((120, 80, 90), dtype=float),
            None,
        )

        with flask_app.app_context():
            draft, err = editor.create_draft_footstep(
                "event-1",
                {
                    "x_min": 5,
                    "x_max": 25,
                    "y_min": 10,
                    "y_max": 30,
                },
            )

        assert draft is None
        assert err == "no_pressure_data"

    def test_create_draft_footstep_accepts_uppercase_bbox_keys(
        self, flask_app, editor, common, event
    ):
        trial_recording = np.zeros((80, 40, 40), dtype=float)
        trial_recording[12:20, 6:12, 4:10] = 1.0

        common._require_event.return_value = (event, None)
        common._load_trial_recording.return_value = (trial_recording, None)

        with flask_app.app_context():
            draft, err = editor.create_draft_footstep(
                "event-1",
                {
                    "XMin": 4,
                    "XMax": 10,
                    "YMin": 6,
                    "YMax": 12,
                },
            )

        assert err is None
        assert draft is not None
        assert draft["XMin"] == 4
        assert draft["XMax"] == 10
        assert draft["YMin"] == 6
        assert draft["YMax"] == 12

    def test_create_footstep_inserts_by_start_frame_and_renumbers_following_ids(
        self, flask_app, editor, common, event, monkeypatch
    ):
        metadata = _make_create_metadata()
        update_csv_mock = MagicMock(return_value=(True, None))
        preprocess_mock = MagicMock(
            return_value=(np.zeros((4, 101, 100, 100), dtype=float), metadata)
        )

        common._require_event.return_value = (event, None)
        common._load_npz_from_uri.side_effect = [
            (np.ones((120, 120), dtype=float), None),
        ]
        common._load_trial_recording.return_value = (
            np.zeros((250, 120, 120), dtype=float),
            None,
        )

        monkeypatch.setattr(
            footstep_edits, "load_metadata", MagicMock(return_value=metadata.copy())
        )
        monkeypatch.setattr(
            footstep_edits, "_is_within_expected_bb_size", lambda row: True
        )
        monkeypatch.setattr(
            footstep_edits, "_is_within_expect_duration", lambda row: True
        )
        monkeypatch.setattr(
            footstep_edits, "identify_anchor_footstep", lambda metadata: None
        )
        monkeypatch.setattr(footstep_edits, "get_heading", lambda row, p100: 0.0)
        monkeypatch.setattr(
            footstep_edits, "reset_path_order", lambda row: int(row["FootstepID"] == 0)
        )
        monkeypatch.setattr(footstep_edits, "trace_path", lambda metadata: None)
        monkeypatch.setattr(footstep_edits, "preprocess_footsteps", preprocess_mock)
        monkeypatch.setattr(footstep_edits.np, "savez_compressed", MagicMock())
        monkeypatch.setattr(footstep_edits.np, "savez", MagicMock())
        monkeypatch.setattr(footstep_edits, "_update_csv", update_csv_mock)

        with flask_app.app_context():
            new_id, err = editor.create_footstep(
                "event-1",
                {
                    "start_frame": 15,
                    "end_frame": 95,
                    "x_min": 12,
                    "x_max": 32,
                    "y_min": 14,
                    "y_max": 44,
                },
            )

        assert new_id == 1
        assert err is None

        updated_metadata = update_csv_mock.call_args.args[0]
        assert list(updated_metadata["FootstepID"]) == [0, 1, 2, 3]

        inserted_row = updated_metadata.loc[updated_metadata["FootstepID"] == 1].iloc[0]
        assert inserted_row["StartFrame"] == 15
        assert inserted_row["EndFrame"] == 95
        assert inserted_row["XMin"] == 12
        assert inserted_row["XMax"] == 32
        assert inserted_row["YMin"] == 14
        assert inserted_row["YMax"] == 44
        assert inserted_row["t"] == 55
        assert inserted_row["x"] == 22
        assert inserted_row["y"] == 29
        assert bool(inserted_row["valid"]) is True

    def test_create_footstep_uses_end_frame_to_break_same_start_frame_ties(
        self, flask_app, editor, common, event, monkeypatch
    ):
        metadata = _make_create_metadata()
        update_csv_mock = MagicMock(return_value=(True, None))

        common._require_event.return_value = (event, None)
        common._load_npz_from_uri.side_effect = [
            (np.ones((120, 120), dtype=float), None),
        ]
        common._load_trial_recording.return_value = (
            np.zeros((250, 120, 120), dtype=float),
            None,
        )

        monkeypatch.setattr(
            footstep_edits, "load_metadata", MagicMock(return_value=metadata.copy())
        )
        monkeypatch.setattr(
            footstep_edits, "_is_within_expected_bb_size", lambda row: True
        )
        monkeypatch.setattr(
            footstep_edits, "_is_within_expect_duration", lambda row: True
        )
        monkeypatch.setattr(
            footstep_edits, "identify_anchor_footstep", lambda metadata: None
        )
        monkeypatch.setattr(footstep_edits, "get_heading", lambda row, p100: 0.0)
        monkeypatch.setattr(footstep_edits, "reset_path_order", lambda row: -1)
        monkeypatch.setattr(footstep_edits, "trace_path", lambda metadata: None)
        monkeypatch.setattr(
            footstep_edits,
            "preprocess_footsteps",
            MagicMock(return_value=(np.zeros((4, 101, 100, 100), dtype=float), None)),
        )
        monkeypatch.setattr(footstep_edits.np, "savez_compressed", MagicMock())
        monkeypatch.setattr(footstep_edits.np, "savez", MagicMock())
        monkeypatch.setattr(footstep_edits, "_update_csv", update_csv_mock)

        with flask_app.app_context():
            new_id, err = editor.create_footstep(
                "event-1",
                {
                    "start_frame": 20,
                    "end_frame": 150,
                    "x_min": 30,
                    "x_max": 50,
                    "y_min": 40,
                    "y_max": 70,
                },
            )

        assert new_id == 2
        assert err is None

        updated_metadata = update_csv_mock.call_args.args[0]
        assert list(updated_metadata["FootstepID"]) == [0, 1, 2, 3]

        inserted_row = updated_metadata.loc[updated_metadata["FootstepID"] == 2].iloc[0]
        assert inserted_row["StartFrame"] == 20
        assert inserted_row["EndFrame"] == 150

        shifted_row = updated_metadata.loc[updated_metadata["FootstepID"] == 3].iloc[0]
        assert shifted_row["StartFrame"] == 30
        assert shifted_row["EndFrame"] == 160


class TestUpdateCsv:
    def test_update_csv_writes_dataframe_to_disk(self, tmp_path, flask_app):
        metadata = pd.DataFrame([{"FootstepID": 1, "valid": True}])
        metadata_path = tmp_path / "metadata.csv"

        with flask_app.app_context():
            ok, err = _update_csv(metadata, metadata_path)

        written = pd.read_csv(metadata_path)

        assert ok is True
        assert err is None
        assert written.to_dict(orient="records") == [{"FootstepID": 1, "valid": True}]

    def test_update_csv_returns_error_when_write_fails(
        self, monkeypatch, tmp_path, flask_app
    ):
        metadata = pd.DataFrame([{"FootstepID": 1, "valid": True}])
        to_csv_mock = MagicMock(side_effect=OSError("permission denied"))
        monkeypatch.setattr(metadata, "to_csv", to_csv_mock)

        with flask_app.app_context():
            ok, err = _update_csv(metadata, tmp_path / "metadata.csv")

        assert ok is False
        assert err == "Error saving metadata.csv: permission denied"
