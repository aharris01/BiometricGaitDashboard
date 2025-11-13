# tests/backend/storage_access_layer/test_db.py

import datetime
import numpy as np
from pathlib import Path

from backend.storage_access_layer.db import (
    DB,
    SwipeEvent,
    get_session,
    engine,
)


# Basic insert + fetch test

def test_add_and_query_swipe_event():
    with get_session() as s:
        ev = SwipeEvent(
            event_id="EV1",
            participant=123,
            date=datetime.date(2025, 1, 1),
            direction="in",
            event_number=1,
            state="complete",           # ← REQUIRED
            trial_npz_uri="test_trial.npz",
            trial_p100_npz_uri="test_p100.npz",
            trial_grf_npz_uri="test_grf.npz",
        )
        s.add(ev)
        s.commit()

    with get_session() as s:
        row = s.get(SwipeEvent, "EV1")
        assert row is not None
        assert row.participant == 123
        assert row.direction == "in"
        assert row.event_number == 1



# full file-path fields

def test_swipe_event_full_paths(tmp_path):
    fp = tmp_path / "trial.npz"
    fp_p100 = tmp_path / "p100.npz"
    fp_grf = tmp_path / "grf.npz"

    np.savez(fp, arr=[1])
    np.savez(fp_p100, arr=[2])
    np.savez(fp_grf, arr=[3])

    with get_session() as s:
        ev = SwipeEvent(
            event_id="EV_FULL",
            participant=111,
            date=datetime.date(2025, 1, 1),
            direction="in",
            event_number=1,
            state="complete",   # ← REQUIRED
            trial_npz_uri=str(fp),
            trial_p100_npz_uri=str(fp_p100),
            trial_grf_npz_uri=str(fp_grf),
        )
        s.add(ev)
        s.commit()

    with get_session() as s:
        row = s.get(SwipeEvent, "EV_FULL")
        assert Path(row.trial_npz_uri).exists()
        assert Path(row.trial_p100_npz_uri).exists()
        assert Path(row.trial_grf_npz_uri).exists()



# handle empty query outputs

def test_db_empty_queries():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from backend.storage_access_layer.db import Base, DB
    import datetime

    # get_session() was struggling here 
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    db = DB(test_engine)

    # Create raw session manually because get_session didn't work here for some reason
    with Session(test_engine) as s:
        assert db.getParticipants(s) == []
        assert db.getDates(s, 99999) == []
        assert db.getDirections(s, 99999, datetime.date(2020, 1, 1)) == []
        assert db.getEvents(s, 99999, datetime.date(2020, 1, 1), "in") == []

# SwipeEventId not found

def test_swipeeventid_not_found():
    db = DB(engine)
    with get_session() as s:
        out = db.getSwipeEventId(
            s,
            participant=99999,
            date=datetime.date(2025, 1, 1),
            event=10,
            direction="in",
        )
        assert out is None


#  BothDirectionEvents returns empty

def test_both_direction_events_empty():
    db = DB(engine)
    with get_session() as s:
        out = db.getBothDirectionEvents(
            s,
            participant=99999,
            date=datetime.date(2025, 1, 1),
        )
        # There are no directions at all → empty list
        assert out == []


# 
#  BothDirectionEvents returns with valid data
#
def test_both_direction_events_with_data():
    with get_session() as s:
        e1 = SwipeEvent(
            event_id="IN1",
            participant=5,
            date=datetime.date(2024, 1, 1),
            direction="in",
            event_number=1,
            state="complete",    
            trial_npz_uri="a.npz",
            trial_p100_npz_uri="b.npz",
            trial_grf_npz_uri="c.npz",
        )
        e2 = SwipeEvent(
            event_id="OUT1",
            participant=5,
            date=datetime.date(2024, 1, 1),
            direction="out",
            event_number=2,
            state="complete",    
            trial_npz_uri="a.npz",
            trial_p100_npz_uri="b.npz",
            trial_grf_npz_uri="c.npz",
        )
        s.add_all([e1, e2])
        s.commit()

    db = DB(engine)
    with get_session() as s:
        out = db.getBothDirectionEvents(s, 5, datetime.date(2024, 1, 1))
        assert out == [[1], [2]]



