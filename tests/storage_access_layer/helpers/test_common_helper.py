from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from backend.storage_access_layer.helpers.common import CommonHelper


@pytest.fixture
def fake_db():
    db = MagicMock()
    db.get_swipe_event = MagicMock()
    return db


@pytest.fixture
def common(fake_db):
    return CommonHelper(fake_db)


@pytest.mark.unit
def test_require_event_returns_missing_event(common, fake_db):
    fake_db.get_swipe_event.return_value = None
    event, err = common._require_event("missing")
    assert event is None
    assert err == "missing_event"


@pytest.mark.unit
def test_get_trial_frame_count_ok(tmp_path, common, fake_db):
    trial = tmp_path / "trial.npz"
    np.savez(trial, arr_0=np.zeros((7, 2, 2)))
    event = SimpleNamespace(trial_npz_uri=trial.as_uri())

    frame_count, err = common._get_trial_frame_count(event)
    assert err is None
    assert frame_count == 7


@pytest.mark.unit
def test_get_p100_array_to_list_returns_unexpected_error(common, fake_db):
    class BrokenArray:
        def tolist(self):
            raise RuntimeError("tolist failed")

    event = SimpleNamespace(trial_p100_npz_uri="file:///fake/path.npz")
    common._load_npz_from_uri = MagicMock(return_value=(BrokenArray(), None))

    data, err = common._get_p100(event)
    assert data is None
    assert err == "unexpected_error"


@pytest.mark.unit
def test_get_p100_return_array_on_success(common):
    array = np.array([[1, 2], [3, 4]])
    expected_list = [[1, 2], [3, 4]]
    event = SimpleNamespace(trial_p100_npz_uri="p100_path")
    common._load_npz_from_uri = MagicMock(return_value=(array, None))

    data, err = common._get_p100(event)
    assert err is None
    assert data == expected_list
