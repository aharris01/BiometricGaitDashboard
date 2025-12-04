# tests/backend/storage_access_layer/test_sal.py

import datetime as dt
from types import SimpleNamespace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock

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
    db.getParticipants = MagicMock()
    db.getDates = MagicMock()
    db.getDirections = MagicMock()
    db.getEvents = MagicMock()
    db.getSwipeEventId = MagicMock()

    # event lookup
    db.getSwipeEvent = MagicMock()

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
def test_sal_getParticipants(sal, fake_db):
    fake_db.getParticipants.return_value = [11111, 22222, 33333]
    out = sal.getParticipants()
    assert out == [11111, 22222, 33333]
    fake_db.getParticipants.assert_called_once()


@pytest.mark.unit
def test_sal_getDates(sal, fake_db):
    d = dt.date(2025, 1, 1)
    fake_db.getDates.return_value = [d]
    out = sal.getDates(11111)
    assert out == [d]
    fake_db.getDates.assert_called_once_with(11111)


@pytest.mark.unit
def test_sal_getDirections(sal, fake_db):
    fake_db.getDirections.return_value = ["in", "out"]
    out = sal.getDirections(11111, dt.date(2025, 1, 1))
    assert out == ["in", "out"]
    fake_db.getDirections.assert_called_once()


@pytest.mark.unit
def test_sal_getEvents(sal, fake_db):
    # MUST be ints per validators
    fake_db.getEvents.return_value = [1, 2, 3]
    out = sal.getEvents(11111, dt.date(2025, 1, 1), "in")
    assert out == [1, 2, 3]
    fake_db.getEvents.assert_called_once()


@pytest.mark.unit
def test_sal_getSwipeEventId(sal, fake_db):
    fake_db.getSwipeEventId.return_value = "EV12345"
    out = sal.getSwipeEventId(11111, dt.date(2025, 1, 1), 1, "in")
    assert out == "EV12345"
    fake_db.getSwipeEventId.assert_called_once()


@pytest.mark.unit
def test_sal_getBothDirectionEvents(sal, fake_db):
    # MUST be dict[str, list[int]]
    fake_db.getDirections.return_value = ["in", "out"]
    fake_db.getEvents.side_effect = [[1, 2], [3, 4]]

    out = sal.getBothDirectionEvents(11111, dt.date(2025, 1, 1))

    assert out == {"in": [1, 2], "out": [3, 4]}
    fake_db.getDirections.assert_called_once()
    assert fake_db.getEvents.call_count == 2
    fake_db.getEvents.side_effect = None


# -------------------------------------------------------------------
# Validation behaviour
# -------------------------------------------------------------------


@pytest.mark.unit
def test_sal_input_validation_failure(sal, fake_db):
    """
    Validators should reject invalid participant type.
    """
    fake_db.getDates.return_value = []
    with pytest.raises(ValueError):
        sal.getDates("not-an-int")  # type: ignore[arg-type]


@pytest.mark.unit
def test_sal_output_validation_failure(sal, fake_db):
    """
    Returning wrong type from DB should trigger validator error.
    """
    fake_db.getDates.return_value = ["not-a-date"]
    with pytest.raises(ValueError):
        sal.getDates(11111)


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

    uri = f"file://{file_path}"
    out = uri_to_path(uri)
    assert out == file_path


# -------------------------------------------------------------------
# getP100
# -------------------------------------------------------------------


@pytest.mark.unit
def test_getP100_ok(tmp_path, sal, fake_db):
    arr = np.array([[1, 2], [3, 4]])
    p = tmp_path / "p100.npz"
    np.savez(p, arr_0=arr)

    fake_db.getSwipeEvent.return_value = SimpleNamespace(
        trial_p100_npz_uri=f"file://{p}"
    )

    out = sal.getP100("evt-1")
    assert out == arr.tolist()
    fake_db.getSwipeEvent.assert_called_once_with("evt-1")


@pytest.mark.unit
def test_getP100_missing_event_returns_none(sal, fake_db):
    fake_db.getSwipeEvent.return_value = None
    out = sal.getP100("missing")
    assert out is None


@pytest.mark.unit
def test_getP100_missing_file_returns_none(tmp_path, sal, fake_db):
    # Point URI at a non-existent file
    missing_path = tmp_path / "no_such_file.npz"
    fake_db.getSwipeEvent.return_value = SimpleNamespace(
        trial_p100_npz_uri=f"file://{missing_path}"
    )
    out = sal.getP100("evt-1")
    assert out is None


# -------------------------------------------------------------------
# getGRF
# -------------------------------------------------------------------


@pytest.mark.unit
def test_getGRF_ok(tmp_path, sal, fake_db):
    arr = np.array([0.1, 0.2, 0.3])
    p = tmp_path / "grf.npz"
    np.savez(p, arr_0=arr)

    fake_db.getSwipeEvent.return_value = SimpleNamespace(
        trial_grf_npz_uri=f"file://{p}"
    )

    data, err = sal.getGRF("evt-1")
    assert err is None
    assert data == arr.tolist()


@pytest.mark.unit
def test_getGRF_missing_event(tmp_path, sal, fake_db):
    fake_db.getSwipeEvent.return_value = None
    data, err = sal.getGRF("missing")
    assert data is None
    assert err == "missing_event"


@pytest.mark.unit
def test_getGRF_missing_file(tmp_path, sal, fake_db):
    missing_path = tmp_path / "no_grf.npz"
    fake_db.getSwipeEvent.return_value = SimpleNamespace(
        trial_grf_npz_uri=f"file://{missing_path}"
    )
    data, err = sal.getGRF("evt-1")
    assert data is None
    assert err == "missing_file"


# -------------------------------------------------------------------
# getFootsteps
# -------------------------------------------------------------------


@pytest.mark.unit
def test_getFootsteps_ok(tmp_path, sal, fake_db):
    # trial file
    trial_path = tmp_path / "trial.npz"
    np.savez(trial_path, arr_0=np.zeros((2, 2)))

    # metadata.csv next to trial
    meta_path = trial_path.with_name("metadata.csv")
    df = pd.DataFrame(
        [
            {
                "FootstepID": 0,
                "StartFrame": 0,
                "EndFrame": 10,
                "XMin": 5,
                "XMax": 15,
                "YMin": 20,
                "YMax": 30,
            }
        ]
    )
    df.to_csv(meta_path, index=False)

    fake_db.getSwipeEvent.return_value = SimpleNamespace(
        trial_npz_uri=f"file://{trial_path}"
    )

    steps, err = sal.getFootsteps("evt-1")
    assert err is None
    assert isinstance(steps, list)
    assert steps[0]["id"] == 0
    assert steps[0]["x_min"] == 5
    assert steps[0]["y_max"] == 30


@pytest.mark.unit
def test_getFootsteps_missing_event(sal, fake_db):
    fake_db.getSwipeEvent.return_value = None
    steps, err = sal.getFootsteps("missing")
    assert steps is None
    assert err == "missing_event"


@pytest.mark.unit
def test_getFootsteps_missing_file(tmp_path, sal, fake_db):
    # trial npz exists but metadata.csv does not
    trial_path = tmp_path / "trial.npz"
    np.savez(trial_path, arr_0=np.zeros((2, 2)))

    fake_db.getSwipeEvent.return_value = SimpleNamespace(
        trial_npz_uri=f"file://{trial_path}"
    )

    steps, err = sal.getFootsteps("evt-1")
    assert steps is None
    assert err == "missing_file"


# -------------------------------------------------------------------
# getFootstepData
# -------------------------------------------------------------------


@pytest.mark.unit
def test_getFootstepData_ok(tmp_path, sal, fake_db):
    # trial npz path
    trial_path = tmp_path / "trial.npz"
    np.savez(trial_path, arr_0=np.zeros((2, 2)))

    # steps.npz: key "0" with a 3D volume (T,H,W)
    vol = np.ones((5, 2, 2))
    steps_path = trial_path.with_name("steps.npz")
    # IMPORTANT: name the array with a keyword so pyright knows it's data, not allow_pickle
    np.savez(steps_path, **{"0": vol})  # type: ignore[arg-type]

    fake_db.getSwipeEvent.return_value = SimpleNamespace(
        trial_npz_uri=f"file://{trial_path}"
    )

    p100, grf, err = sal.getFootstepData("evt-1", 0)
    assert err is None
    assert p100 == np.max(vol, axis=0).tolist()
    assert grf == vol.reshape(vol.shape[0], -1).sum(axis=1).tolist()


@pytest.mark.unit
def test_getFootstepData_missing_event(sal, fake_db):
    fake_db.getSwipeEvent.return_value = None
    p100, grf, err = sal.getFootstepData("missing", 0)
    assert p100 is None and grf is None
    assert err == "missing_event"


@pytest.mark.unit
def test_getFootstepData_missing_file(tmp_path, sal, fake_db):
    # trial npz exists but steps.npz does not
    trial_path = tmp_path / "trial.npz"
    np.savez(trial_path, arr_0=np.zeros((2, 2)))

    fake_db.getSwipeEvent.return_value = SimpleNamespace(
        trial_npz_uri=f"file://{trial_path}"
    )

    p100, grf, err = sal.getFootstepData("evt-1", 0)
    assert p100 is None and grf is None
    assert err == "missing_file"
