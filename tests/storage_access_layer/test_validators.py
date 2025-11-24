# tests/test_validators.py
import datetime
import pytest

from backend.storage_access_layer import validators as v


@pytest.mark.unit
def test_getParticipants_check_valid():
    v.getParticipants_check([1, 2, 3])


@pytest.mark.unit
def test_getParticipants_check_invalid():
    with pytest.raises(ValueError):
        v.getParticipants_check([1, "bad", 3])


@pytest.mark.unit
def test_getDates_check_valid():
    v.getDates_check(1, [datetime.date(2025, 1, 1)])


@pytest.mark.unit
def test_getDates_check_invalid_date():
    with pytest.raises(ValueError):
        v.getDates_check(1, ["not-a-date"])


@pytest.mark.unit
def test_getDirections_check_invalid_direction():
    with pytest.raises(ValueError):
        v.getDirections_check(1, datetime.date.today(), ["sideways"])


@pytest.mark.unit
def test_getEvents_check_invalid_event():
    with pytest.raises(ValueError):
        v.getEvents_check(1, datetime.date.today(), "in", ["not-int"])


@pytest.mark.unit
def test_getSwipeEventId_check_invalid_return():
    with pytest.raises(ValueError):
        v.getSwipeEventId_check(1, datetime.date.today(), 1, "in", 123)


@pytest.mark.unit
def test_getBothDirectionEvents_check_invalid_nested():
    with pytest.raises(ValueError):
        v.getBothDirectionEvents_check(1, datetime.date.today(), [[1], ["bad"]])
