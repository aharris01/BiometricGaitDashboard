# tests/backend/storage_access_layer/test_db.py

import datetime
import numpy as np
from pathlib import Path
import pytest

from backend.storage_access_layer.db import swipe_event


# Basic insert + fetch test


@pytest.mark.unit
def test_add_and_query_swipe_event(test_db):
    swipe_event_obj = swipe_event(
        event_id="EV1",
        participant=123,
        date=datetime.date(2025, 1, 1),
        direction="in",
        event_number=1,
        state="complete",  # ← REQUIRED
        trial_npz_uri="test_trial.npz",
        trial_p100_npz_uri="test_p100.npz",
        trial_grf_npz_uri="test_grf.npz",
    )

    test_db.add_swipe_event(swipe_event_obj)

    with test_db._get_session() as s:
        row = s.get(swipe_event, "EV1")
        assert row is not None
        assert row.participant == 123
        assert row.direction == "in"
        assert row.event_number == 1


# full file-path fields


@pytest.mark.unit
def test_swipe_event_full_paths(tmp_path, test_db):
    fp = tmp_path / "trial.npz"
    fp_p100 = tmp_path / "p100.npz"
    fp_grf = tmp_path / "grf.npz"

    np.savez(fp, arr=[1])
    np.savez(fp_p100, arr=[2])
    np.savez(fp_grf, arr=[3])

    with test_db._get_session() as s:
        ev = swipe_event(
            event_id="EV_FULL",
            participant=111,
            date=datetime.date(2025, 1, 1),
            direction="in",
            event_number=1,
            state="complete",  # ← REQUIRED
            trial_npz_uri=str(fp),
            trial_p100_npz_uri=str(fp_p100),
            trial_grf_npz_uri=str(fp_grf),
        )
        s.add(ev)
        s.commit()

    with test_db._get_session() as s:
        row = s.get(swipe_event, "EV_FULL")
        assert Path(row.trial_npz_uri).exists()
        assert Path(row.trial_p100_npz_uri).exists()
        assert Path(row.trial_grf_npz_uri).exists()


# handle empty query outputs


@pytest.mark.unit
def test_db_empty_queries(empty_db):
    db = empty_db

    # Create raw session manually because get_session didn't work here for some reason
    assert db.get_participants() == []
    assert db.get_dates(99999) == []
    assert db.get_directions(99999, datetime.date(2020, 1, 1)) == []
    assert db.get_events(99999, datetime.date(2020, 1, 1), "in") == []


# SwipeEventId not found


@pytest.mark.unit
def test_swipe_eventid_not_found(empty_db):
    db = empty_db
    out = db.get_swipe_event_id(
        participant=99999,
        date=datetime.date(2025, 1, 1),
        event=10,
        direction="in",
    )
    assert out is None
