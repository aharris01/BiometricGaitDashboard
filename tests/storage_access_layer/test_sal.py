# tests/backend/storage_access_layer/test_sal.py

from __future__ import annotations

import csv
import datetime as dt
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pytest

import backend.storage_access_layer.sal as sal_mod
from backend.storage_access_layer.sal import SAL, uri_to_path


def _write_npz_with_numeric_keys(path: Path, arrays: dict[str, np.ndarray]) -> None:
    """
    Create an .npz file that np.load can read with numeric string keys like "0", "1".

    This avoids pyright issues with np.savez(**{"0": ...}) while keeping runtime behavior
    identical for SAL (which expects keys like "0" in steps.npz).
    """
    with ZipFile(path, mode="w", compression=ZIP_DEFLATED) as zf:
        for key, arr in arrays.items():
            buf = BytesIO()
            np.save(buf, arr)
            zf.writestr(f"{key}.npy", buf.getvalue())


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------


@pytest.fixture
def fake_db():
    """
    A fake DB object with all required methods mocked.

    IMPORTANT:
    SAL now calls snake_case DB methods (get_swipe_event),
    so we must mock that (and optionally alias camelCase for safety).
    """
    db = MagicMock()

    # meta-lookup methods
    db.get_participants = MagicMock()
    db.get_dates = MagicMock()
    db.get_directions = MagicMock()
    db.get_events = MagicMock()
    db.get_swipe_event_id = MagicMock()

    # event lookup (snake_case is what SAL uses now)
    db.get_swipe_event = MagicMock()

    # optional alias so older code/tests won't break
    db.getSwipeEvent = db.get_swipe_event  # type: ignore[attr-defined]

    # close method so SAL._close_db() is happy
    db.close = MagicMock()

    return db


@pytest.fixture
def sal(fake_db):
    """Create a SAL instance with a mocked DB."""
    return SAL(db=fake_db)


# -------------------------------------------------------------------
# DB Operation tests
# -------------------------------------------------------------------


@pytest.mark.unit
def test_close_db_calls_close(sal, fake_db):
    fake_db.close.reset_mock()
    sal._close_db()
    fake_db.close.assert_called_once()


@pytest.mark.unit
def test_close_db_no_db_noop(sal, fake_db):
    sal.db = None
    sal._close_db()
    fake_db.close.assert_not_called()


@pytest.mark.unit
def test_close_db_no_close_attr_noop(sal):
    sal.db = SimpleNamespace()  # no close attr
    sal._close_db()  # should not raise


# -------------------------------------------------------------------
# Meta lookup tests
# -------------------------------------------------------------------


@pytest.mark.unit
def test_sal_get_participants(sal, fake_db):
    fake_db.get_participants.return_value = [11111, 22222, 33333]
    out = sal.get_participants()
    assert out == [11111, 22222, 33333]
    fake_db.get_participants.assert_called_once()


@pytest.mark.unit
def test_sal_get_dates(sal, fake_db):
    d = dt.date(2025, 1, 1)
    fake_db.get_dates.return_value = [d]
    out = sal.get_dates(11111)
    assert out == [d]
    fake_db.get_dates.assert_called_once_with(11111)


@pytest.mark.unit
def test_sal_get_directions(sal, fake_db):
    fake_db.get_directions.return_value = ["in", "out"]
    out = sal.get_directions(11111, dt.date(2025, 1, 1))
    assert out == ["in", "out"]
    fake_db.get_directions.assert_called_once()


@pytest.mark.unit
def test_sal_get_events(sal, fake_db):
    # MUST be ints per validators
    fake_db.get_events.return_value = [1, 2, 3]
    out = sal.get_events(11111, dt.date(2025, 1, 1), "in")
    assert out == [1, 2, 3]
    fake_db.get_events.assert_called_once()


@pytest.mark.unit
def test_sal_get_swipe_event_id(sal, fake_db):
    fake_db.get_swipe_event_id.return_value = "EV12345"
    out = sal.get_swipe_event_id(11111, dt.date(2025, 1, 1), 1, "in")
    assert out == "EV12345"
    fake_db.get_swipe_event_id.assert_called_once()


@pytest.mark.unit
def test_sal_get_both_direction_events(sal, fake_db):
    # MUST be dict[str, list[int]]
    fake_db.get_directions.return_value = ["in", "out"]
    fake_db.get_events.side_effect = [[1, 2], [3, 4]]

    out = sal.get_both_direction_events(11111, dt.date(2025, 1, 1))

    assert out == {"in": [1, 2], "out": [3, 4]}
    fake_db.get_directions.assert_called_once()
    assert fake_db.get_events.call_count == 2
    fake_db.get_events.side_effect = None


# -------------------------------------------------------------------
# Validation behaviour
# -------------------------------------------------------------------


@pytest.mark.unit
def test_sal_input_validation_failure(sal, fake_db):
    """
    Validators should reject invalid participant type.
    """
    fake_db.get_dates.return_value = []
    with pytest.raises(ValueError):
        sal.get_dates("not-an-int")  # type: ignore[arg-type]


@pytest.mark.unit
def test_sal_output_validation_failure(sal, fake_db):
    """
    Returning wrong type from DB should trigger validator error.
    """
    fake_db.get_dates.return_value = ["not-a-date"]
    with pytest.raises(ValueError):
        sal.get_dates(11111)


# -------------------------------------------------------------------
# File/URI helpers
# -------------------------------------------------------------------


@pytest.mark.unit
def test_uri_to_path_roundtrip(tmp_path):
    file_path = tmp_path / "test.npz"
    file_path.write_bytes(b"dummy")

    uri = file_path.as_uri()
    out = uri_to_path(uri)
    assert out == file_path


# -------------------------------------------------------------------
# get_p100
# -------------------------------------------------------------------


@pytest.mark.unit
def test_get_p100_ok(tmp_path, sal, fake_db):
    arr = np.array([[1, 2], [3, 4]])
    p = tmp_path / "p100.npz"
    np.savez(p, arr_0=arr)

    fake_db.get_swipe_event.return_value = SimpleNamespace(
        trial_p100_npz_uri=p.as_uri()
    )

    out = sal.get_p100("evt-1")
    assert out == arr.tolist()
    fake_db.get_swipe_event.assert_called_once_with("evt-1")


@pytest.mark.unit
def test_get_p100_missing_event_returns_none(sal, fake_db):
    fake_db.get_swipe_event.return_value = None
    out = sal.get_p100("missing")
    assert out is None


@pytest.mark.unit
def test_get_p100_missing_file_returns_none(tmp_path, sal, fake_db):
    # Point URI at a non-existent file
    missing_path = tmp_path / "no_such_file.npz"
    fake_db.get_swipe_event.return_value = SimpleNamespace(
        trial_p100_npz_uri=missing_path.as_uri()
    )
    out = sal.get_p100("evt-1")
    assert out is None


# -------------------------------------------------------------------
# get_grf
# -------------------------------------------------------------------


@pytest.mark.unit
def test_get_grf_ok(tmp_path, sal, fake_db):
    arr = np.array([0.1, 0.2, 0.3])
    p = tmp_path / "grf.npz"
    np.savez(p, arr_0=arr)

    fake_db.get_swipe_event.return_value = SimpleNamespace(trial_grf_npz_uri=p.as_uri())

    data, err = sal.get_grf("evt-1")
    assert err is None
    assert data == arr.tolist()


@pytest.mark.unit
def test_get_grf_missing_event(tmp_path, sal, fake_db):
    fake_db.get_swipe_event.return_value = None
    data, err = sal.get_grf("missing")
    assert data is None
    assert err == "missing_event"


@pytest.mark.unit
def test_get_grf_missing_file(tmp_path, sal, fake_db):
    missing_path = tmp_path / "no_grf.npz"
    fake_db.get_swipe_event.return_value = SimpleNamespace(
        trial_grf_npz_uri=missing_path.as_uri()
    )
    data, err = sal.get_grf("evt-1")
    assert data is None
    assert err == "missing_file"


# -------------------------------------------------------------------
# get_footsteps
# -------------------------------------------------------------------


@pytest.mark.unit
def test_get_footsteps_ok(tmp_path, sal, fake_db):
    # trial file
    trial_path = tmp_path / "trial.npz"
    np.savez(trial_path, arr_0=np.zeros((2, 2)))

    meta_path = trial_path.with_name("metadata.csv")
    with meta_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "FootstepID",
                "StartFrame",
                "EndFrame",
                "XMin",
                "XMax",
                "YMin",
                "YMax",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "FootstepID": 0,
                "StartFrame": 10,
                "EndFrame": 20,
                "XMin": 1,
                "XMax": 5,
                "YMin": 2,
                "YMax": 6,
            }
        )

    fake_db.get_swipe_event.return_value = SimpleNamespace(
        trial_npz_uri=trial_path.as_uri()
    )

    steps, err = sal.get_footsteps("evt-1")
    assert err is None
    assert isinstance(steps, list)

    step0 = steps[0]
    assert step0["id"] == 0
    assert step0["start_frame"] == 10
    assert step0["end_frame"] == 20
    assert step0["x_min"] == 1
    assert step0["x_max"] == 5
    assert step0["y_min"] == 2
    assert step0["y_max"] == 6


@pytest.mark.unit
def test_get_footsteps_missing_event(sal, fake_db):
    fake_db.get_swipe_event.return_value = None
    steps, err = sal.get_footsteps("missing")
    assert steps is None
    assert err == "missing_event"


@pytest.mark.unit
def test_get_footsteps_missing_file(tmp_path, sal, fake_db):
    # trial npz exists but metadata.csv does not
    trial_path = tmp_path / "trial.npz"
    np.savez(trial_path, arr_0=np.zeros((2, 2)))

    fake_db.get_swipe_event.return_value = SimpleNamespace(
        trial_npz_uri=trial_path.as_uri()
    )

    steps, err = sal.get_footsteps("evt-1")
    assert steps is None
    assert err == "missing_file"


# -------------------------------------------------------------------
# get_footstep_data
# -------------------------------------------------------------------


@pytest.mark.unit
def test_get_footstep_data_ok(tmp_path, sal, fake_db):
    trial_path = tmp_path / "trial.npz"
    np.savez(trial_path, arr_0=np.zeros((2, 2)))

    vol = np.ones((5, 2, 2))
    steps_path = trial_path.with_name("steps.npz")
    _write_npz_with_numeric_keys(steps_path, {"0": vol})

    fake_db.get_swipe_event.return_value = SimpleNamespace(
        trial_npz_uri=trial_path.as_uri()
    )

    p100, grf, err = sal.get_footstep_data("evt-1", 0)
    assert err is None
    assert p100 == np.max(vol, axis=0).tolist()
    assert grf == vol.reshape(vol.shape[0], -1).sum(axis=1).tolist()


@pytest.mark.unit
def test_get_footstep_data_missing_event(sal, fake_db):
    fake_db.get_swipe_event.return_value = None
    p100, grf, err = sal.get_footstep_data("missing", 0)
    assert p100 is None and grf is None
    assert err == "missing_event"


@pytest.mark.unit
def test_get_footstep_data_missing_file(tmp_path, sal, fake_db):
    trial_path = tmp_path / "trial.npz"
    np.savez(trial_path, arr_0=np.zeros((2, 2)))

    fake_db.get_swipe_event.return_value = SimpleNamespace(
        trial_npz_uri=trial_path.as_uri()
    )

    p100, grf, err = sal.get_footstep_data("evt-1", 0)
    assert p100 is None and grf is None
    assert err == "missing_file"


@pytest.mark.unit
def test_get_all_footstep_p100_missing_event(sal, fake_db):
    fake_db.get_swipe_event.return_value = None
    items, err = sal.get_all_footstep_p100("missing")
    assert items is None and err == "missing_event"


@pytest.mark.unit
def test_get_all_footstep_p100_missing_file(tmp_path, sal, fake_db):
    trial = tmp_path / "trial.npz"
    np.savez(trial, arr_0=np.zeros((1, 1)))
    fake_db.get_swipe_event.return_value = SimpleNamespace(trial_npz_uri=trial.as_uri())

    items, err = sal.get_all_footstep_p100("evt-1")
    assert items is None and err == "missing_file"


@pytest.mark.unit
def test_get_all_footstep_p100_ok(tmp_path, sal, fake_db):
    trial = tmp_path / "trial.npz"
    np.savez(trial, arr_0=np.zeros((1, 1)))

    steps_path = trial.with_name("steps.npz")
    _write_npz_with_numeric_keys(
        steps_path,
        {
            "2": np.array([[[1, 2]], [[3, 4]]]),  # max -> [[3,4]]
            "0": np.array([[[5, 6]]]),  # max -> [[5,6]]
        },
    )

    fake_db.get_swipe_event.return_value = SimpleNamespace(trial_npz_uri=trial.as_uri())

    items, err = sal.get_all_footstep_p100("evt-1")
    assert err is None
    assert items == [
        {"id": 0, "p100": [[5, 6]]},
        {"id": 2, "p100": [[3, 4]]},
    ]


@pytest.mark.unit
def test_get_all_footstep_p100_invalid_key(tmp_path, sal, fake_db):
    trial = tmp_path / "trial.npz"
    np.savez(trial, arr_0=np.zeros((1, 1)))
    steps_path = trial.with_name("steps.npz")
    np.savez(steps_path, abc=np.zeros((1, 1, 1)))  # int("abc") fails

    fake_db.get_swipe_event.return_value = SimpleNamespace(trial_npz_uri=trial.as_uri())

    items, err = sal.get_all_footstep_p100("evt-1")
    assert items is None and err == "missing_file"


# -------------------------------------------------------------------
# Get Event Summary
# -------------------------------------------------------------------


@pytest.mark.unit
def test_get_event_summary_missing_event(sal, fake_db):
    fake_db.get_swipe_event.return_value = None
    assert sal.get_event_summary("missing") is None
    fake_db.get_swipe_event.assert_called_once_with("missing")


@pytest.mark.unit
def test_get_event_summary_ok(tmp_path, sal, fake_db):
    p100 = tmp_path / "p100.npz"
    np.savez(p100, arr_0=np.zeros((1, 1)))
    grf = tmp_path / "grf.npz"
    np.savez(grf, arr_0=np.zeros((1,)))
    trial = tmp_path / "trial.npz"
    np.savez(trial, arr_0=np.zeros((1, 1)))
    (trial.with_name("metadata.csv")).write_text(
        "FootstepID,StartFrame,EndFrame,XMin,XMax,YMin,YMax\n"
    )
    (trial.with_name("steps.npz")).write_bytes(b"")

    event = SimpleNamespace(
        event_id="e1",
        participant=123,
        date=dt.date(2024, 1, 1),
        direction="in",
        event_number=1,
        state="ready",
        trial_p100_npz_uri=p100.as_uri(),
        trial_grf_npz_uri=grf.as_uri(),
        trial_npz_uri=trial.as_uri(),
    )
    fake_db.get_swipe_event.return_value = event

    event_dict, availability = sal.get_event_summary("e1")
    assert event_dict == {
        "event_id": "e1",
        "participant": 123,
        "date": "2024-01-01",
        "direction": "in",
        "event_number": 1,
        "state": "ready",
    }
    assert availability == {"p100": True, "grf": True, "metadata": True, "steps": True}


@pytest.mark.unit
def test_get_event_summary_missing_files(tmp_path, sal, fake_db):
    trial = tmp_path / "trial.npz"
    np.savez(trial, arr_0=np.zeros((1, 1)))
    event = SimpleNamespace(
        event_id="e2",
        participant=999,
        date=None,
        direction="out",
        event_number=2,
        state="done",
        trial_p100_npz_uri=(tmp_path / "no_p100.npz").as_uri(),
        trial_grf_npz_uri="file:///definitely/invalid/path",
        trial_npz_uri=trial.as_uri(),
    )
    fake_db.get_swipe_event.return_value = event

    event_dict, availability = sal.get_event_summary("e2")
    assert event_dict["date"] is None
    assert availability == {
        "p100": False,
        "grf": False,
        "metadata": False,
        "steps": False,
    }


@pytest.mark.unit
def test_get_event_summary_invalid_uri(sal, fake_db):
    event = SimpleNamespace(
        event_id="e3",
        participant=1,
        date=None,
        direction="in",
        event_number=3,
        state="bad",
        trial_p100_npz_uri="http://not-file",
        trial_grf_npz_uri="http://not-file",
        trial_npz_uri="http://not-file",
    )
    fake_db.get_swipe_event.return_value = event
    _, availability = sal.get_event_summary("e3")
    assert availability == {
        "p100": False,
        "grf": False,
        "metadata": False,
        "steps": False,
    }


@pytest.mark.unit
def test_uri_to_path_invalid_scheme_raises():
    with pytest.raises(ValueError):
        uri_to_path("not-a-uri-at-all")


@pytest.mark.unit
def test_get_event_id_from_URI_calls_get_swipe_event_id(sal, fake_db):
    fake_db.get_swipe_event_id.return_value = "EVT123"

    uri = r"data\100\2023-10-31\out\12\metadata.csv"

    out = sal.get_event_id_from_URI(uri)

    assert out == "EVT123"
    fake_db.get_swipe_event_id.assert_called_once_with(
        100,
        dt.date(2023, 10, 31),
        12,
        "out",
    )


# -------------------------------------------------------------------
# Summary plot helpers (extra coverage to push CI over 80%)
# -------------------------------------------------------------------


@pytest.mark.unit
def test_get_swipe_event_summary_plot_data_scans_and_computes(tmp_path, fake_db):
    # Point SAL's module-level dataroot at tmp_path so rglob finds our file
    sal_mod.dataroot = str(tmp_path)
    s = SAL(db=fake_db)

    fake_db.get_swipe_event_id.return_value = "EVT999"

    meta = tmp_path / "data" / "100" / "2024-01-01" / "in" / "7" / "metadata.csv"
    meta.parent.mkdir(parents=True, exist_ok=True)
    with meta.open("w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "FootstepID",
                "StartFrame",
                "EndFrame",
                "XMin",
                "XMax",
                "YMin",
                "YMax",
            ],
        )
        w.writeheader()
        # bbox areas: 10*5=50 and 4*2=8 => avg = 29
        w.writerow(
            {
                "FootstepID": "0",
                "StartFrame": "0",
                "EndFrame": "1",
                "XMin": "0",
                "XMax": "10",
                "YMin": "0",
                "YMax": "5",
            }
        )
        w.writerow(
            {
                "FootstepID": "1",
                "StartFrame": "2",
                "EndFrame": "3",
                "XMin": "1",
                "XMax": "5",
                "YMin": "2",
                "YMax": "4",
            }
        )

    out = s.get_swipe_event_summary_plot_data()

    assert "EVT999" in out
    assert out["EVT999"]["footstep_count"] == 2
    assert out["EVT999"]["avg_box_size"] == 29

    fake_db.get_swipe_event_id.assert_called_once_with(
        100,
        dt.date(2024, 1, 1),
        7,
        "in",
    )
