from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock

import pytest

from backend.storage_access_layer.helpers.sal_metrics import SalMetrics


@pytest.fixture
def fake_db():
    db = MagicMock()
    db._get_session = MagicMock()
    return db


@pytest.fixture
def helper(fake_db):
    return SalMetrics(fake_db, common=MagicMock())


@pytest.mark.unit
def test_get_available_metrics_excludes_event_id(helper):
    items = helper.get_available_metrics()
    assert "event_id" not in items
    assert "avg_bbox_size" in items


@pytest.mark.unit
def test_get_distinct_date_values_invalid_part_raises(helper):
    with pytest.raises(ValueError):
        helper.get_distinct_date_values("hour")


@pytest.mark.unit
def test_get_date_bounds_empty_returns_none(helper, fake_db):
    fake_session = MagicMock()
    fake_session.execute.return_value.first.return_value = (None, None)
    fake_db._get_session.return_value.__enter__.return_value = fake_session

    out = helper.get_date_bounds()
    assert out == {"min_date": None, "max_date": None}
