# tests/backend/storage_access_layer/test_sal.py

import datetime
import pytest
from unittest.mock import MagicMock

from backend.storage_access_layer.SAL import SAL


@pytest.fixture
def fake_db():
    """A fake DB object with all required methods mocked."""
    db = MagicMock()
    db.getParticipants = MagicMock()
    db.getDates = MagicMock()
    db.getDirections = MagicMock()
    db.getEvents = MagicMock()
    db.getSwipeEventId = MagicMock()
    db.getBothDirectionEvents = MagicMock()
    return db


@pytest.fixture
def sal(fake_db):
    """Create a SAL instance with a mocked DB."""
    sal = SAL(db=fake_db)
    yield sal
    sal.db.close()

# Tests

def test_sal_getParticipants(sal, fake_db):
    fake_db.getParticipants.return_value = [11111, 22222, 33333]
    out = sal.getParticipants()
    assert out == [11111, 22222, 33333]
    fake_db.getParticipants.assert_called_once()


def test_sal_getDates(sal, fake_db):
    d = datetime.date(2025, 1, 1)
    fake_db.getDates.return_value = [d]
    out = sal.getDates(11111)
    assert out == [d]
    fake_db.getDates.assert_called_once()


def test_sal_getDirections(sal, fake_db):
    fake_db.getDirections.return_value = ["in", "out"]
    out = sal.getDirections(11111, datetime.date(2025, 1, 1))
    assert out == ["in", "out"]
    fake_db.getDirections.assert_called_once()


def test_sal_getEvents(sal, fake_db):
    # MUST be ints per validators
    fake_db.getEvents.return_value = [1, 2, 3]
    out = sal.getEvents(11111, datetime.date(2025, 1, 1), "in")
    assert out == [1, 2, 3]
    fake_db.getEvents.assert_called_once()


def test_sal_getSwipeEventId(sal, fake_db):
    fake_db.getSwipeEventId.return_value = "EV12345"
    out = sal.getSwipeEventId(11111, datetime.date(2025, 1, 1), 1, "in")
    assert out == "EV12345"
    fake_db.getSwipeEventId.assert_called_once()


def test_sal_getBothDirectionEvents(sal, fake_db):
    # MUST be list[list[int]]
    fake_db.getBothDirectionEvents.return_value = [[1, 2], [3, 4]]
    out = sal.getBothDirectionEvents(11111, datetime.date(2025, 1, 1))
    assert out == [[1, 2], [3, 4]]
    fake_db.getBothDirectionEvents.assert_called_once()

def test_sal_input_validation_failure(sal, fake_db):
    # validators should reject invalid types
    fake_db.getDates.return_value = []
    with pytest.raises(ValueError):
        sal.getDates("not-an-int")


def test_sal_output_validation_failure(sal, fake_db):
    # returning wrong type should trigger validator error
    fake_db.getDates.return_value = ["not-a-date"]
    with pytest.raises(ValueError):
        sal.getDates(11111)


