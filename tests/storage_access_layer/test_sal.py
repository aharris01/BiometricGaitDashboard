# tests/backend/storage_access_layer/test_sal.py
import csv
import datetime as dt
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from backend.storage_access_layer.sal import SAL, uri_to_path


@pytest.fixture
def fake_db():
    db = MagicMock()

    # ✅ SAL uses snake_case DB methods
    db.get_participants = MagicMock()
    db.get_dates = MagicMock()
    db.get_directions = MagicMock()
    db.get_events = MagicMock()
    db.get_swipe_event_id = MagicMock()

    db.get_swipe_event = MagicMock()
    db.close = MagicMock()
    return db


@pytest.fixture
def sal(fake_db):
    return SAL(db=fake_db)


@pytest.mark.unit
def test_sal_getParticipants(sal, fake_db):
    fake_db.get_participants.return_value = [11111, 22222, 33333]
    out = sal.getParticipants()
    assert out == [11111, 22222, 33333]
    fake_db.get_participants.assert_called_once()


@pytest.mark.unit
def test_sal_getDates(sal, fake_db):
    d = dt.date(2025, 1, 1)
    fake_db.get_dates.return_value = [d]
    out = sal.getDates(11111)
    assert out == [d]
    fake_db.get_dates.assert_called_once_with(11111)


@pytest.mark.unit
def test_sal_getDirections(sal, fake_db):
    fake_db.get_directions.return_value = ["in", "out"]
    out = sal.getDirections(11111, dt.date(2025, 1, 1))
    assert out == ["in", "out"]
    fake_db.get_directions.assert_called_once()


@pytest.mark.unit
def test_sal_getEvents(sal, fake_db):
    fake_db.get_events.return_value = [1, 2, 3]
    out = sal.getEvents(11111, dt.date(2025, 1, 1), "in")
    assert out == [1, 2, 3]
    fake_db.get_events.assert_called_once()


@pytest.mark.unit
def test_sal_getSwipeEventId(sal, fake_db):
    fake_db.get_swipe_event_id.return_value = "EV12345"
    out = sal.getSwipeEventId(11111, dt.date(2025, 1, 1), 1, "in")
    assert out == "EV12345"
    fake_db.get_swipe_event_id.assert_called_once()


@pytest.mark.unit
def test_uri_to_path_roundtrip(tmp_path):
    file_path = tmp_path / "test.npz"
    file_path.write_bytes(b"dummy")
    uri = f"file://{file_path}"
    out = uri_to_path(uri)
    assert out == file_path


@pytest.mark.unit
def test_getP100_ok(tmp_path, sal, fake_db):
    arr = np.array([[1, 2], [3, 4]])
    p = tmp_path / "p100.npz"
    np.savez(p, arr_0=arr)

    fake_db.get_swipe_event.return_value = SimpleNamespace(trial_p100_npz_uri=f"file://{p}")

    out = sal.getP100("evt-1")
    assert out == arr.tolist()
    fake_db.get_swipe_event.assert_called_once_with("evt-1")
