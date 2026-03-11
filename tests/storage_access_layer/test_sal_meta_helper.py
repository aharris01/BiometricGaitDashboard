from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock

import pytest

from backend.storage_access_layer.helpers.sal_meta import SalMeta


@pytest.fixture
def fake_db():
    db = MagicMock()
    db.get_participants = MagicMock(return_value=[100, 200])
    db.get_dates = MagicMock(return_value=[dt.date(2025, 1, 1)])
    db.get_directions = MagicMock(return_value=["in", "out"])
    db.get_events = MagicMock(return_value=[1, 2])
    db.get_swipe_event_id = MagicMock(return_value="EVT-1")
    return db


@pytest.fixture
def helper(fake_db):
    return SalMeta(fake_db, common=MagicMock())


@pytest.mark.unit
def test_get_participants(helper):
    assert helper.get_participants() == [100, 200]


@pytest.mark.unit
def test_get_swipe_event_id(helper):
    assert helper.get_swipe_event_id(100, dt.date(2025, 1, 1), 1, "in") == "EVT-1"
