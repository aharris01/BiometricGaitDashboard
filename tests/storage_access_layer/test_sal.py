# tests/backend/storage_access_layer/test_sal.py

import csv
import datetime as dt
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from backend.storage_access_layer.sal import SAL, uri_to_path


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

    # meta-lookup methods (SAL calls snake_case now)
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
# Meta lookup tests
# -------------------------------------------------------------------


@pytest.mark.unit
def test_sal_getParticipants(sal, fake_db):
    fake_db.get_participants.return_value = [11111, 22222, 33333]
    out = sal.getParticipants()
    assert out == [11111, 22222, 33333]
    fake_db.get_participants.assert_called_once()



@pytest.mark.unit
def test_sal_getDates(sal, fake_db):
    d = dt.date(2025, 1, 1)
    fake_db.get_dates.return_value = [d]
    out = sal.getDates(11111)
    assert out == [d]
    fake_db.get_dates.assert_called_once_with(11111)



@pytest.mark.unit
def test_sal_getDirections(sal, fake_db):
    fake_db.get_directions.return_value = ["in", "out"]
    out = sal.getDirections(11111, dt.date(2025, 1, 1))
    assert out == ["in", "out"]
    fake_db.get_directions.assert_called_once()



@pytest.mark.unit
def test_sal_getEvents(sal, fake_db):
    fake_db.get_events.return_value = [1, 2, 3]
    out = sal.getEvents(11111, dt.date(2025, 1, 1), "in")
    assert out == [1, 2, 3]
    fake_db.get_events.assert_called_once()



@pytest.mark.unit
def test_sal_getSwipeEventId(sal, fake_db):
    fake_db.get_swipe_event_id.return_value = "EV12345"
    out = sal.getSwipeEventId(11111, dt.date(2025, 1, 1), 1, "in")
    assert out == "EV12345"
    fake_db.get_swipe_event_id.assert_called_once()


@pytest.mark.unit
def test_sal_getBothDirectionEvents(sal, fake_db):
    fake_db.get_directions.return_value = ["in", "out"]
    fake_db.get_events.side_effect = [[1, 2], [3, 4]]

    out = sal.getBothDirectionEvents(11111, dt.date(2025, 1, 1))

    assert out == {"in": [1, 2], "out": [3, 4]}
    fake_db.get_directions.assert_called_once()
    assert fake_db.get_events.call_count == 2
    fake_db.get_events.side_effect = None



# -------------------------------------------------------------------
# Validation behaviour
# -------------------------------------------------------------------


@pytest.mark.unit
def test_sal_input_validation_failure(sal, fake_db):
    fake_db.get_dates.return_value = []
    with pytest.raises(ValueError):
        sal.getDates("not-an-int")  # type: ignore[arg-type]


@pytest.mark.unit
def test_sal_output_validation_failure(sal, fake_db):
    fake_db.get_dates.return_value = ["not-a-date"]
    with pytest.raises(ValueError):
        sal.getDates(11111)


# -------------------------------------------------------------------
# File/URI helpers
# -------------------------------------------------------------------


@pytest.mark.unit
def test_uri_to_path_roundtrip(tmp_path):
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

    fake_db.get_swipe_event.return_value = SimpleNamespace(
        trial_p100_npz_uri=f"file://{p}"
    )

    out = sal.getP100("evt-1")
    assert out == arr.tolist()
    fake_db.get_swipe_event.assert_called_once_with("evt-1")


@pytest.mark.unit
def test_getP100_missing_event_returns_none(sal, fake_db):
    fake_db.get_swipe_event.return_value = None
    out = sal.getP100("missing")
    assert out is None


@pytest.mark.unit
def test_getP100_missing_file_returns_none(tmp_path, sal, fake_db):
    missing_path = tmp_path / "no_such_file.npz"
    fake_db.get_swipe_event.return_value = SimpleNamespace(
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

    fake_db.get_swipe_event.return_value = SimpleNamespace(
        trial_grf_npz_uri=f"file://{p}"
    )

    data, err = sal.getGRF("evt-1")
    assert err is None
    assert data == arr.tolist()


@pytest.mark.unit
def test_getGRF_missing_event(tmp_path, sal, fake_db):
    fake_db.get_swipe_event.return_value = None
    data, err = sal.getGRF("missing")
    assert data is None
    assert err == "missing_event"


@pytest.mark.unit
def test_getGRF_missing_file(tmp_path, sal, fake_db):
    missing_path = tmp_path / "no_grf.npz"
    fake_db.get_swipe_event.return_value = SimpleNamespace(
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
        trial_npz_uri=f"file://{trial_path}"
    )

    steps, err = sal.getFootsteps("evt-1")
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
def test_getFootsteps_missing_event(sal, fake_db):
    fake_db.get_swipe_event.return_value = None
    steps, err = sal.getFootsteps("missing")
    assert steps is None
    assert err == "missing_event"


@pytest.mark.unit
def test_getFootsteps_missing_file(tmp_path, sal, fake_db):
    trial_path = tmp_path / "trial.npz"
    np.savez(trial_path, arr_0=np.zeros((2, 2)))

    fake_db.get_swipe_event.return_value = SimpleNamespace(
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
    trial_path = tmp_path / "trial.npz"
    np.savez(trial_path, arr_0=np.zeros((2, 2)))

    vol = np.ones((5, 2, 2))
    steps_path = trial_path.with_name("steps.npz")
    np.savez(steps_path, **{"0": vol})  # type: ignore[arg-type]

    fake_db.get_swipe_event.return_value = SimpleNamespace(
        trial_npz_uri=f"file://{trial_path}"
    )

    p100, grf, err = sal.getFootstepData("evt-1", 0)
    assert err is None
    assert p100 == np.max(vol, axis=0).tolist()
    assert grf == vol.reshape(vol.shape[0], -1).sum(axis=1).tolist()


@pytest.mark.unit
def test_getFootstepData_missing_event(sal, fake_db):
    fake_db.get_swipe_event.return_value = None
    p100, grf, err = sal.getFootstepData("missing", 0)
    assert p100 is None and grf is None
    assert err == "missing_event"


@pytest.mark.unit
def test_getFootstepData_missing_file(tmp_path, sal, fake_db):
    trial_path = tmp_path / "trial.npz"
    np.savez(trial_path, arr_0=np.zeros((2, 2)))

    fake_db.get_swipe_event.return_value = SimpleNamespace(
        trial_npz_uri=f"file://{trial_path}"
    )

    p100, grf, err = sal.getFootstepData("evt-1", 0)
    assert p100 is None and grf is None
    assert err == "missing_file"


# -------------------------------------------------------------------
# NEW coverage helpers: getEventSummary + getAllFootstepP100
# -------------------------------------------------------------------


@pytest.mark.unit
def test_getEventSummary_ok(tmp_path, sal, fake_db):
    trial_path = tmp_path / "trial.npz"
    p100_path = tmp_path / "trial.p100.npz"
    grf_path = tmp_path / "trial.grf.npz"

    np.savez(trial_path, arr_0=np.zeros((2, 2)))
    np.savez(p100_path, arr_0=np.zeros((2, 2)))
    np.savez(grf_path, arr_0=np.zeros((10,)))

    # files SAL checks beside trial
    (trial_path.with_name("metadata.csv")).write_text(
        "FootstepID,StartFrame,EndFrame,XMin,XMax,YMin,YMax\n"
    )
    np.savez(trial_path.with_name("steps.npz"), **{"0": np.ones((2, 2, 2))})

    fake_db.get_swipe_event.return_value = SimpleNamespace(
        event_id="evt-1",
        participant=1,
        date=dt.date(2025, 1, 1),
        direction="in",
        event_number=1,
        state="ready",
        trial_npz_uri=f"file://{trial_path}",
        trial_p100_npz_uri=f"file://{p100_path}",
        trial_grf_npz_uri=f"file://{grf_path}",
    )

    out = sal.getEventSummary("evt-1")
    assert out is not None
    event_dict, availability = out

    assert event_dict["event_id"] == "evt-1"
    assert availability["p100"] is True
    assert availability["grf"] is True
    assert availability["metadata"] is True
    assert availability["steps"] is True


@pytest.mark.unit
def test_getAllFootstepP100_ok(tmp_path, sal, fake_db):
    trial_path = tmp_path / "trial.npz"
    np.savez(trial_path, arr_0=np.zeros((2, 2)))

    steps_path = trial_path.with_name("steps.npz")
    np.savez(
        steps_path,
        **{
            "2": np.ones((3, 2, 2)),
            "1": np.ones((4, 2, 2)) * 2,
        },
    )

    fake_db.get_swipe_event.return_value = SimpleNamespace(
        trial_npz_uri=f"file://{trial_path}"
    )

    items, err = sal.getAllFootstepP100("evt-1")
    assert err is None
    assert items is not None
    assert [x["id"] for x in items] == [1, 2]  # sorted
    assert isinstance(items[0]["p100"], list)


@pytest.mark.unit
def test_getAllFootstepP100_missing_event(sal, fake_db):
    fake_db.get_swipe_event.return_value = None
    items, err = sal.getAllFootstepP100("missing")
    assert items is None
    assert err == "missing_event"
