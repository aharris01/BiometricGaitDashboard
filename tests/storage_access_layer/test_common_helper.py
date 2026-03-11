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
    fake_db.get_swipe_event.return_value = SimpleNamespace(trial_npz_uri=trial.as_uri())

    frame_count, err = common._get_trial_frame_count("evt-1")
    assert err is None
    assert frame_count == 7


@pytest.mark.unit
def test_get_p100_missing_event(common, fake_db):
    fake_db.get_swipe_event.return_value = None
    data, err = common._get_p100("evt-1")
    assert data is None
    assert err == "missing_event"
