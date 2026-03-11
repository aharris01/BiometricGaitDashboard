from __future__ import annotations

import datetime as dt
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from backend.storage_access_layer.helpers.sal_events import SalEvents


@pytest.fixture
def fake_db():
    db = MagicMock()
    db.get_swipe_event = MagicMock()
    return db


@pytest.fixture
def common():
    obj = MagicMock()
    obj._require_event = MagicMock()
    obj._load_npz_from_uri = MagicMock()
    obj._get_p100 = MagicMock()
    return obj


@pytest.fixture
def helper(fake_db, common):
    return SalEvents(fake_db, common)


@pytest.mark.unit
def test_get_p100_returns_none_on_common_error(helper, common):
    common._get_p100.return_value = (None, "missing_file")
    assert helper.get_p100("evt-1") is None


@pytest.mark.unit
def test_get_grf_ok(helper, common):
    common._require_event.return_value = (
        SimpleNamespace(trial_grf_npz_uri="file:///tmp/grf.npz"),
        None,
    )
    common._load_npz_from_uri.return_value = (np.array([1.0, 2.0]), None)
    data, err = helper.get_grf("evt-1")
    assert err is None
    assert data == [1.0, 2.0]


@pytest.mark.unit
def test_get_event_summary_missing_event(helper, fake_db):
    fake_db.get_swipe_event.return_value = None
    assert helper.get_event_summary("missing") is None


@pytest.mark.unit
def test_get_event_summary_maps_basic_fields(helper, fake_db):
    fake_db.get_swipe_event.return_value = SimpleNamespace(
        event_id="evt-1",
        participant=100,
        date=dt.date(2025, 1, 1),
        direction="in",
        event_number=1,
        trial_p100_npz_uri="http://bad",
        trial_grf_npz_uri="http://bad",
        trial_npz_uri="http://bad",
    )
    event, availability = helper.get_event_summary("evt-1")
    assert event["event_id"] == "evt-1"
    assert event["date"] == "2025-01-01"
    assert availability == {"p100": False, "grf": False, "metadata": False, "steps": False}
