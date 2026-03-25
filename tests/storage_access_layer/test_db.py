import datetime

import pytest

from backend.storage_access_layer.db.schema import (
    LocalSwipeEvent,
    LocalMetrics,
    ManifestSwipeEvent,
    ManifestFootstep,
    LocalFootstep,
)
from backend.storage_access_layer.db.db import (
    copy_metrics_from_manifest_to_local,
    copy_footsteps_from_manifest_to_local,
)

pytestmark = pytest.mark.unit


def test_get_participants_dates_directions_events(seeded_db):
    assert seeded_db.get_participants() == [11111]
    assert seeded_db.get_dates(11111) == [datetime.date(2025, 1, 1)]
    assert seeded_db.get_directions(11111, datetime.date(2025, 1, 1)) == ["in"]
    assert seeded_db.get_events(11111, datetime.date(2025, 1, 1), "in") == [1]


def test_get_swipe_event_builds_paths(seeded_db, tmp_path):
    event = seeded_db.get_swipe_event("EV_PRESENT")
    assert event is not None
    # expected_root = Path(seeded_db.get_local_event_ids()[0]).name  # event_id
    assert event.event_id == "EV_PRESENT"
    assert event.trial_npz_uri.endswith("trial.npz")
    assert event.trial_p100_npz_uri.endswith("trial.p100.npz")
    assert event.trial_grf_npz_uri.endswith("trial.grf.npz")


def test_get_swipe_event_id_missing(empty_db):
    out = empty_db.get_swipe_event_id(
        participant=99999,
        date=datetime.date(2020, 1, 1),
        event=1,
        direction="in",
    )
    assert out is None


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


def test_copy_metrics_upserts(seeded_db):
    # first call inserts
    inserted = copy_metrics_from_manifest_to_local(seeded_db)
    assert inserted in (0, 1)
    # second call updates, rowcount still >=0 (sqlite returns 0 on no-op update)
    again = copy_metrics_from_manifest_to_local(seeded_db)
    assert again in (0, 1)
    with seeded_db._get_session() as s:
        row = s.get(LocalMetrics, "EV_PRESENT")
        assert row.avg_bbox_size == 3.14
        assert row.step_count == 7


def test_empty_queries_return_lists(empty_db):
    assert empty_db.get_participants() == []
    assert empty_db.get_dates(123) == []
    assert empty_db.get_directions(123, datetime.date(2020, 1, 1)) == []
    assert empty_db.get_events(123, datetime.date(2020, 1, 1), "in") == []


def _seed_footstep_search_data(db):
    now = datetime.datetime.now()

    with db._get_session() as s:
        # Swipe-event metadata in manifest
        s.add_all(
            [
                ManifestSwipeEvent(
                    event_id="EV_1",
                    participant=11111,
                    date=datetime.date(2025, 1, 1),
                    direction="in",
                    event_number=1,
                    local=1,
                ),
                ManifestSwipeEvent(
                    event_id="EV_2",
                    participant=22222,
                    date=datetime.date(2025, 1, 2),
                    direction="out",
                    event_number=2,
                    local=1,
                ),
            ]
        )

        # Local availability
        s.add_all(
            [
                LocalSwipeEvent(
                    event_id="EV_1",
                    root_path="/tmp/ev1",
                    present=True,
                    last_seen=now,
                ),
                LocalSwipeEvent(
                    event_id="EV_2",
                    root_path="/tmp/ev2",
                    present=True,
                    last_seen=now,
                ),
            ]
        )

        # Manifest footsteps that will be copied into local_footsteps
        s.add_all(
            [
                ManifestFootstep(
                    event_id="EV_1",
                    footstep_id=1,
                    start_frame=10,
                    end_frame=20,
                    x_min=0,
                    x_max=20,  # width = 20
                    y_min=0,
                    y_max=30,  # height = 30
                ),
                ManifestFootstep(
                    event_id="EV_2",
                    footstep_id=1,
                    start_frame=15,
                    end_frame=25,
                    x_min=0,
                    x_max=50,  # width = 50
                    y_min=0,
                    y_max=60,  # height = 60
                ),
            ]
        )

    copied = copy_footsteps_from_manifest_to_local(db)
    assert copied in (0, 1, 2)


def test_copy_footsteps_upserts(empty_db):
    _seed_footstep_search_data(empty_db)

    with empty_db._get_session() as s:
        row_1 = s.get(LocalFootstep, ("EV_1", 1))
        row_2 = s.get(LocalFootstep, ("EV_2", 1))

        assert row_1 is not None
        assert row_2 is not None
        assert row_1.x_max - row_1.x_min == 20
        assert row_2.y_max - row_2.y_min == 60


def test_search_footsteps_filters_by_participant(empty_db):
    _seed_footstep_search_data(empty_db)

    rows, total = empty_db.search_footsteps(participants=[11111])

    assert total == 1
    assert len(rows) == 1
    assert rows[0]["event_id"] == "EV_1"
    assert rows[0]["participant"] == 11111


def test_search_footsteps_filters_by_date_range(empty_db):
    _seed_footstep_search_data(empty_db)

    rows, total = empty_db.search_footsteps(
        date_from=datetime.date(2025, 1, 2),
        date_to=datetime.date(2025, 1, 2),
    )

    assert total == 1
    assert len(rows) == 1
    assert rows[0]["event_id"] == "EV_2"
    assert rows[0]["date"] == datetime.date(2025, 1, 2)


def test_search_footsteps_filters_by_width_and_height(empty_db):
    _seed_footstep_search_data(empty_db)

    rows, total = empty_db.search_footsteps(
        width_min=15,
        width_max=25,
        height_min=25,
        height_max=35,
    )

    assert total == 1
    assert len(rows) == 1
    assert rows[0]["event_id"] == "EV_1"
    assert rows[0]["bbox_width"] == 20
    assert rows[0]["bbox_height"] == 30


def test_search_footsteps_filters_by_size(empty_db):
    _seed_footstep_search_data(empty_db)

    rows, total = empty_db.search_footsteps(
        size_min=2500,
        size_max=3500,
    )

    assert total == 1
    assert len(rows) == 1
    assert rows[0]["event_id"] == "EV_2"
    assert rows[0]["bbox_area"] == 3000


def test_search_footsteps_respects_offset_and_limit(empty_db):
    _seed_footstep_search_data(empty_db)

    rows, total = empty_db.search_footsteps(offset=1, limit=1)

    assert total == 2
    assert len(rows) == 1
    assert rows[0]["event_id"] == "EV_2"


def test_delete_local_footstep_returns_none_when_row_missing(empty_db):
    deleted = empty_db.delete_local_footstep("EV_MISSING", 4)

    assert deleted is None


def test_create_local_footstep_defaults_step_archive_key_to_local_id(empty_db):
    row = empty_db.create_local_footstep(
        "EV_TEST",
        start_frame=10,
        end_frame=20,
        x_min=1,
        x_max=11,
        y_min=2,
        y_max=12,
        label=None,
    )

    assert row is not None
    assert row.footstep_id == 0
    assert row.step_archive_key == 0


def test_update_step_archive_keys_updates_existing_rows(empty_db):
    empty_db.create_local_footstep(
        "EV_TEST",
        start_frame=10,
        end_frame=20,
        x_min=1,
        x_max=11,
        y_min=2,
        y_max=12,
        label=None,
        step_archive_key=6,
    )
    empty_db.create_local_footstep(
        "EV_TEST",
        start_frame=30,
        end_frame=40,
        x_min=3,
        x_max=13,
        y_min=4,
        y_max=14,
        label=None,
        step_archive_key=7,
    )

    updated = empty_db.update_step_archive_keys("EV_TEST", {6: 0, 7: 1})

    assert updated == 2

    with empty_db._get_session() as session:
        first = session.get(LocalFootstep, ("EV_TEST", 0))
        second = session.get(LocalFootstep, ("EV_TEST", 1))

        assert first is not None
        assert second is not None
        assert first.step_archive_key == 0
        assert second.step_archive_key == 1
