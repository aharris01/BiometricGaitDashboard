from __future__ import annotations

import datetime as dt
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pytest

from backend.storage_access_layer.helpers.sal_footsteps import SalFootsteps


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
    db.get_local_footstep_changes = MagicMock(return_value=[])
    db.update_local_footstep = MagicMock()
    db.create_local_footstep = MagicMock()
    db.delete_local_footstep = MagicMock()
    return db


@pytest.fixture
def common():
    obj = MagicMock()
    obj._require_event = MagicMock(return_value=(SimpleNamespace(), None))
    obj._get_p100 = MagicMock(return_value=([[1.0, 2.0], [3.0, 4.0]], None))
    obj._get_image_dims = MagicMock(return_value=(2, 2, None))
    obj._get_trial_frame_count = MagicMock(return_value=(20, None))
    obj._load_steps_npz = MagicMock()
    return obj


@pytest.fixture
def helper(fake_db, common):
    return SalFootsteps(fake_db, common)


@pytest.mark.unit
def test_search_footsteps_maps_rows(helper, fake_db):
    fake_db.search_footsteps.return_value = (
        [
            {
                "event_id": "evt-1",
                "footstep_id": 2,
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
                "has_thumbnail": True,
            }
        ],
        1,
    )
    out = helper.search_footsteps(event_ids=["evt-1", ""], participants=[11111])
    assert out["total"] == 1
    assert out["items"][0]["date"] == "2025-01-01"


@pytest.mark.unit
def test_get_footsteps_missing_event(helper, common):
    common._require_event.return_value = (None, "missing_event")
    steps, err = helper.get_footsteps("evt-1")
    assert steps is None
    assert err == "missing_event"


@pytest.mark.unit
def test_get_footstep_data_missing_key(tmp_path, helper, common):
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
