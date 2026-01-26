from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pytest

from backend.storage_access_layer.sal import SAL


def _write_npz_with_numeric_keys(path, arrays: dict[str, np.ndarray]) -> None:
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


@pytest.fixture
def fake_db():
    # Minimal stub: only what these SAL methods call
    class DBStub:
        def __init__(self):
            self._event = None

        def get_swipe_event(self, event_id):
            return self._event

        def close(self):
            pass

    return DBStub()


@pytest.fixture
def sal(fake_db):
    return SAL(db=fake_db)


@pytest.mark.unit
def test_get_p100_invalid_uri_returns_none(sal, fake_db):
    # uri_to_path should raise ValueError if scheme != file
    fake_db._event = SimpleNamespace(trial_p100_npz_uri="http://example.com/p100.npz")
    out = sal.get_p100("evt-1")
    assert out is None


@pytest.mark.unit
def test_get_grf_reads_non_arr0_first_key(tmp_path, sal, fake_db):
    # Exercise the "first key" branch (not arr_0)
    p = tmp_path / "grf.npz"
    np.savez(p, foo=np.array([1.0, 2.0, 3.0]))  # no arr_0

    fake_db._event = SimpleNamespace(trial_grf_npz_uri=p.resolve().as_uri())
    data, err = sal.get_grf("evt-1")
    assert err is None
    assert data == [1.0, 2.0, 3.0]


@pytest.mark.unit
def test_get_footsteps_bad_csv_returns_missing_file(tmp_path, sal, fake_db):
    # metadata.csv exists but missing required columns -> missing_file
    trial = tmp_path / "trial.npz"
    np.savez(trial, arr_0=np.zeros((2, 2)))

    meta = trial.with_name("metadata.csv")
    meta.write_text("FootstepID,StartFrame\n0,10\n")  # missing lots of columns

    fake_db._event = SimpleNamespace(trial_npz_uri=trial.resolve().as_uri())
    steps, err = sal.get_footsteps("evt-1")
    assert steps is None
    assert err == "missing_file"


@pytest.mark.unit
def test_get_footstep_data_missing_step_key(tmp_path, sal, fake_db):
    trial = tmp_path / "trial.npz"
    np.savez(trial, arr_0=np.zeros((2, 2)))

    # steps.npz exists, but key "0" not present
    steps_path = trial.with_name("steps.npz")
    _write_npz_with_numeric_keys(steps_path, {"1": np.ones((2, 2, 2))})

    fake_db._event = SimpleNamespace(trial_npz_uri=trial.resolve().as_uri())
    p100, grf, err = sal.get_footstep_data("evt-1", 0)
    assert p100 is None and grf is None
    assert err == "missing_file"


@pytest.mark.unit
def test_get_all_footstep_p100_missing_file(tmp_path, sal, fake_db):
    trial = tmp_path / "trial.npz"
    np.savez(trial, arr_0=np.zeros((2, 2)))

    # steps.npz intentionally NOT created
    fake_db._event = SimpleNamespace(trial_npz_uri=trial.resolve().as_uri())
    items, err = sal.get_all_footstep_p100("evt-1")
    assert items is None
    assert err == "missing_file"


@pytest.mark.unit
def test_get_all_footstep_details_ok(tmp_path, sal, fake_db):
    trial = tmp_path / "trial.npz"
    np.savez(trial, arr_0=np.zeros((2, 2)))

    vol0 = np.ones((3, 2, 2))
    vol1 = np.ones((4, 2, 2)) * 2

    steps_path = trial.with_name("steps.npz")
    _write_npz_with_numeric_keys(steps_path, {"0": vol0, "1": vol1})

    fake_db._event = SimpleNamespace(trial_npz_uri=trial.resolve().as_uri())
    items, err = sal.get_all_footstep_details("evt-1")

    assert err is None
    assert items is not None
    assert [x["id"] for x in items] == [0, 1]  # sorted
    assert "p100" in items[0] and "grf" in items[0]
    assert isinstance(items[0]["p100"], list)
    assert isinstance(items[0]["grf"], list)


@pytest.mark.unit
def test_get_all_footstep_details_missing_file(tmp_path, sal, fake_db):
    trial = tmp_path / "trial.npz"
    np.savez(trial, arr_0=np.zeros((2, 2)))

    # steps.npz intentionally missing
    fake_db._event = SimpleNamespace(trial_npz_uri=trial.resolve().as_uri())
    items, err = sal.get_all_footstep_details("evt-1")
    assert items is None
    assert err == "missing_file"
