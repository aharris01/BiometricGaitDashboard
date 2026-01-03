# tests/backend/storage_access_layer/test_sal.py

import csv
import datetime as dt
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from backend.storage_access_layer.SAL import SAL, uri_to_path


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------


@pytest.fixture
def fake_db():
    """
    A fake DB object with all required methods mocked.
    """
    db = MagicMock()

    # meta-lookup methods
    db.get_participants = MagicMock()
    db.get_dates = MagicMock()
    db.get_directions = MagicMock()
    db.get_events = MagicMock()
    db.get_swipe_event_id = MagicMock()

    # event lookup
    db.get_swipe_event = MagicMock()

    # close method so SAL._close_db() is happy
    db.close = MagicMock()

    return db


@pytest.fixture
def sal(fake_db):
    """Create a SAL instance with a mocked DB."""
    return SAL(db=fake_db)


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
    """
    uri_to_path should convert file:// URIs into the same local Path.
    """
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
# get_foot_steps
# -------------------------------------------------------------------


@pytest.mark.unit
def test_get_footsteps_ok(tmp_path, sal, fake_db):
    # trial file
    trial_path = tmp_path / "trial.npz"
    np.savez(trial_path, arr_0=np.zeros((2, 2)))

    # metadata.csv next to trial
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

    steps, err = sal.get_foot_steps("evt-1")
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
    steps, err = sal.get_foot_steps("missing")
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

    steps, err = sal.get_foot_steps("evt-1")
    assert steps is None
    assert err == "missing_file"


# -------------------------------------------------------------------
# get_footstep_data
# -------------------------------------------------------------------


@pytest.mark.unit
def test_get_footstep_data_ok(tmp_path, sal, fake_db):
    # trial npz path
    trial_path = tmp_path / "trial.npz"
    np.savez(trial_path, arr_0=np.zeros((2, 2)))

    # steps.npz: key "0" with a 3D volume (T,H,W)
    vol = np.ones((5, 2, 2))
    steps_path = trial_path.with_name("steps.npz")
    # IMPORTANT: name the array with a keyword so pyright knows it's data, not allow_pickle
    np.savez(steps_path, **{"0": vol})  # type: ignore[arg-type]

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
    # trial npz exists but steps.npz does not
    trial_path = tmp_path / "trial.npz"
    np.savez(trial_path, arr_0=np.zeros((2, 2)))

    fake_db.get_swipe_event.return_value = SimpleNamespace(
        trial_npz_uri=trial_path.as_uri()
    )

    p100, grf, err = sal.get_footstep_data("evt-1", 0)
    assert p100 is None and grf is None
    assert err == "missing_file"
