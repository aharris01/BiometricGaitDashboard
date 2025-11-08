# tests/test_accessfunctions.py
import os
# use on-disk sqlite database for testing. avoids shared-memory issues on windows
os.environ["DATABASE_URL"] = "sqlite:///test_temp.db"

import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# import from the backend storage access layer
from backend.storage_access_layer import db
from backend.storage_access_layer.db import Base, SwipeEvent
from backend.storage_access_layer.accessfunctions import (
    getParticipants,
    getDates,
    getDirections,
    getEvents,
    getSwipeEventId,
    getBothDirectionEvents,
)

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    # create on-disk sqlite. temp database for testing 
    test_engine = create_engine("sqlite:///test_temp.db")

    # rebind backend engine and session maker to shared test engine
    db.engine = test_engine
    db.SessionLocal.configure(bind=test_engine)

    # create database schema for testing
    Base.metadata.create_all(test_engine)

    # simple test data, should simulate real swipe event data
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

    # use context manager to populate temp db
    with Session(test_engine) as session:
        session.add_all(test_data)
        session.commit()

    # yield allows setup before tests and teardown after tests
    yield  

    # teardown the test database and dispose of engine resources
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()

    # remove temp file when done
    if os.path.exists("test_temp.db"):
        os.remove("test_temp.db")


# -------------------- TESTS -------------------- #

def test_getParticipants():
    assert sorted(getParticipants()) == [11111, 22222, 33333]

def test_getDates():
    assert getDates(11111) == [datetime.date(2025, 1, 1)]

def test_getDirections():
    assert getDirections(22222, datetime.date(2025, 1, 2)) == ["out"]

def test_getEvents():
    assert getEvents(33333, datetime.date(2025, 1, 3), "in") == [3]

def test_getSwipeEventId():
    result = getSwipeEventId(11111, datetime.date(2025, 1, 1), 1, "in")
    assert result == "test_11111_2025-01-01_in_1_complete"

def test_getSwipeEventId_nonexistent():
    result = getSwipeEventId(99999, datetime.date(2025, 1, 1), 1, "in")
    assert result is None

# new function test for getBothDirectionEvents
def test_getBothDirectionEvents():
    result = getBothDirectionEvents(22222, datetime.date(2025, 1, 2))
    # should return a 2D list even if only one direction exists
    assert isinstance(result, list)
    assert all(isinstance(inner, list) for inner in result)

