import datetime

from backend.storage_access_layer.accessfunctions import (
    getParticipants,
    getDates,
    getDirections,
    getEvents,
    getSwipeEventId,
    getBothDirectionEvents,
)

#TESTS

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

