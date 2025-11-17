# tests/backend/storage_access_layer/test_db.py

import datetime
import numpy as np
from pathlib import Path

from backend.storage_access_layer.db import SwipeEvent


# Basic insert + fetch test


def test_add_and_query_swipe_event(test_db):
    swipe_event = SwipeEvent(
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

    test_db.addSwipeEvent(swipe_event)

    with test_db._get_session() as s:
        row = s.get(SwipeEvent, "EV1")
        assert row is not None
        assert row.participant == 123
        assert row.direction == "in"
        assert row.event_number == 1


# full file-path fields


def test_swipe_event_full_paths(tmp_path, test_db):
    fp = tmp_path / "trial.npz"
    fp_p100 = tmp_path / "p100.npz"
    fp_grf = tmp_path / "grf.npz"

    np.savez(fp, arr=[1])
    np.savez(fp_p100, arr=[2])
    np.savez(fp_grf, arr=[3])

    with test_db._get_session() as s:
        ev = SwipeEvent(
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
        row = s.get(SwipeEvent, "EV_FULL")
        assert Path(row.trial_npz_uri).exists()
        assert Path(row.trial_p100_npz_uri).exists()
        assert Path(row.trial_grf_npz_uri).exists()


# handle empty query outputs


def test_db_empty_queries(empty_db):
    db = empty_db

    # Create raw session manually because get_session didn't work here for some reason
    assert db.getParticipants() == []
    assert db.getDates(99999) == []
    assert db.getDirections(99999, datetime.date(2020, 1, 1)) == []
    assert db.getEvents(99999, datetime.date(2020, 1, 1), "in") == []


# SwipeEventId not found


def test_swipe_eventid_not_found(empty_db):
    db = empty_db
    out = db.getSwipeEventId(
        participant=99999,
        date=datetime.date(2025, 1, 1),
        event=10,
        direction="in",
    )
    assert out is None
