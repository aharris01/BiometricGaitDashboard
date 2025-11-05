# tests/test_accessfunctions.py
import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"


import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.storage_access_layer.db import Base, SwipeEvent
from backend.storage_access_layer.accessfunctions import (
    getParticipants,
    getDates,
    getDirections,
    getEvents,
    getSwipeEventId,
)

@pytest.fixture(scope="module")
def session():
    #create in memory sql lite. temp database for testing 
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)

    #simple test data, should simulate real swipe event data
    test_data = [
        SwipeEvent(
            event_id="test_11111_2025-01-01_in_1_complete",
            participant=11111,
            date=datetime.date(2025, 1, 1),
            direction="in",
            event_number=1,
            state="complete",
            trial_npz_uri="file://test/11111/2025-01-01/in/1/trial.npz",
            trial_p100_npz_uri="file://test/11111/2025-01-01/in/1/trial.p100.npz",
            trial_grf_npz_uri="file://test/11111/2025-01-01/in/1/trial.grf.npz",
        ),
        SwipeEvent(
            event_id="test_22222_2025-01-02_out_2_complete",
            participant=22222,
            date=datetime.date(2025, 1, 2),
            direction="out",
            event_number=2,
            state="complete",
            trial_npz_uri="file://test/22222/2025-01-02/out/2/trial.npz",
            trial_p100_npz_uri="file://test/22222/2025-01-02/out/2/trial.p100.npz",
            trial_grf_npz_uri="file://test/22222/2025-01-02/out/2/trial.grf.npz",
        ),
        SwipeEvent(
            event_id="test_33333_2025-01-03_in_3_complete",
            participant=33333,
            date=datetime.date(2025, 1, 3),
            direction="in",
            event_number=3,
            state="complete",
            trial_npz_uri="file://test/33333/2025-01-03/in/3/trial.npz",
            trial_p100_npz_uri="file://test/33333/2025-01-03/in/3/trial.p100.npz",
            trial_grf_npz_uri="file://test/33333/2025-01-03/in/3/trial.grf.npz",
        ),
    ]

    session.add_all(test_data)
    session.commit()
    #use yield to provide session to tests
    yield session  

    #equivelant to closing things down when the tests are complete
    session.close()
    Base.metadata.drop_all(engine)

#tests

def test_getParticipants(session):
    assert sorted(getParticipants(session)) == [11111, 22222, 33333]

def test_getDates(session):
    assert getDates(session, 11111) == [datetime.date(2025, 1, 1)]

def test_getDirections(session):
    assert getDirections(session, 22222, datetime.date(2025, 1, 2)) == ["out"]

def test_getEvents(session):
    assert getEvents(session, 33333, datetime.date(2025, 1, 3), "in") == [3]

def test_getSwipeEventId(session):
    result = getSwipeEventId(session, 11111, datetime.date(2025, 1, 1), 1, "in")
    assert result == "test_11111_2025-01-01_in_1_complete"

def test_getSwipeEventId_nonexistent(session):
    result = getSwipeEventId(session, 99999, datetime.date(2025, 1, 1), 1, "in")
    assert result is None

