import datetime
from pathlib import Path


import pytest

from backend.storage_access_layer.db.schema import (
    LocalSwipeEvent,
    LocalMetrics,
)
from backend.storage_access_layer.db.db import copy_metrics_from_manifest_to_local


@pytest.mark.unit
def test_get_participants_dates_directions_events(seeded_db):
    assert seeded_db.get_participants() == [11111]
    assert seeded_db.get_dates(11111) == [datetime.date(2025, 1, 1)]
    assert seeded_db.get_directions(11111, datetime.date(2025, 1, 1)) == ["in"]
    assert seeded_db.get_events(11111, datetime.date(2025, 1, 1), "in") == [1]


@pytest.mark.unit
def test_get_swipe_event_builds_paths(seeded_db, tmp_path):
    event = seeded_db.get_swipe_event("EV_PRESENT")
    assert event is not None
    # expected_root = Path(seeded_db.get_local_event_ids()[0]).name  # event_id
    assert event.event_id == "EV_PRESENT"
    assert event.trial_npz_uri.endswith("trial.npz")
    assert event.trial_p100_npz_uri.endswith("trial.p100.npz")
    assert event.trial_grf_npz_uri.endswith("trial.grf.npz")


@pytest.mark.unit
def test_get_swipe_event_id_missing(empty_db):
    out = empty_db.get_swipe_event_id(
        participant=99999,
        date=datetime.date(2020, 1, 1),
        event=1,
        direction="in",
    )
    assert out is None


@pytest.mark.unit
def test_add_swipe_event_inserts_local_record(empty_db, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    obj = LocalSwipeEvent(
        event_id="NEW_EVENT",
        root_path=str(root),
        present=True,
        last_seen=datetime.datetime.now(),
    )
    empty_db.add_swipe_event(obj)
    assert "NEW_EVENT" in empty_db.get_local_event_ids()


@pytest.mark.unit
def test_copy_metrics_upserts(seeded_db):
    # first call inserts
    inserted = copy_metrics_from_manifest_to_local(seeded_db)
    assert inserted in (0, 1)
    # second call updates, rowcount still >=0 (sqlite returns 0 on no-op update)
    again = copy_metrics_from_manifest_to_local(seeded_db)
    assert again in (0, 1)
    with seeded_db._get_session() as s:
        row = s.get(LocalMetrics, "EV_PRESENT")
        assert row.average_bounding_box_size == 3.14
        assert row.step_count == 7


@pytest.mark.unit
def test_empty_queries_return_lists(empty_db):
    assert empty_db.get_participants() == []
    assert empty_db.get_dates(123) == []
    assert empty_db.get_directions(123, datetime.date(2020, 1, 1)) == []
    assert empty_db.get_events(123, datetime.date(2020, 1, 1), "in") == []
