from __future__ import annotations

import os
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from backend.storage_access_layer.helpers.common import CommonHelper


@pytest.fixture
def fake_db():
    db = MagicMock()
    db.get_swipe_event = MagicMock()
    return db


@pytest.fixture
def common(fake_db):
    return CommonHelper(fake_db)


@pytest.mark.unit
def test_require_event_returns_missing_event(common, fake_db):
    fake_db.get_swipe_event.return_value = None
    event, err = common._require_event("missing")
    assert event is None
    assert err == "missing_event"


@pytest.mark.unit
def test_get_trial_frame_count_ok(tmp_path, common, fake_db):
    trial = tmp_path / "trial.grf.npz"
    np.savez_compressed(trial, allow_pickle=False, **{"[:,:]": np.zeros((7, 1))})
    event = SimpleNamespace(trial_grf_npz_uri=trial.as_uri())

    frame_count, err = common._get_trial_frame_count(event)
    assert err is None
    assert frame_count == 7


@pytest.mark.unit
def test_get_p100_ndarray_on_success(common):
    array = np.array([[1, 2], [3, 4]])
    event = SimpleNamespace(trial_p100_npz_uri="p100_path")
    common._load_npz_from_uri = MagicMock(return_value=(array, None))

    data, err = common._get_p100(event)
    assert err is None
    assert data.shape == array.shape
    assert data.dtype == array.dtype
    assert data.all() == array.all()


@pytest.mark.unit
def test_load_steps_npz_returns_archive_handle(tmp_path, common):
    trial = tmp_path / "trial.npz"
    steps = tmp_path / "steps.npz"
    np.savez_compressed(trial, arr_0=np.zeros((2, 2)))
    np.savez_compressed(
        steps, **{"0": np.ones((2, 2, 2)), "1": np.full((1, 2, 2), 3.0)}
    )
    event = SimpleNamespace(trial_npz_uri=trial.as_uri())

    loaded, err = common._load_steps_npz(event)

    assert err is None
    assert loaded is not None
    assert sorted(loaded.files) == ["0", "1"]
    np.testing.assert_array_equal(loaded["0"], np.ones((2, 2, 2)))
    np.testing.assert_array_equal(loaded["1"], np.full((1, 2, 2), 3.0))
    loaded.close()


@pytest.mark.unit
def test_load_trial_recording_caches_full_trial_array(tmp_path, common):
    trial = tmp_path / "trial.npz"
    array = np.arange(24, dtype=np.uint16).reshape(2, 3, 4)
    np.savez_compressed(trial, arr_0=array)
    event = SimpleNamespace(event_id="evt-1", trial_npz_uri=trial.as_uri())
    common._trial_recording_cache_dir = tmp_path / "cache"

    loaded, err = common._load_trial_recording(event)

    assert err is None
    np.testing.assert_array_equal(loaded, array)
    cache_path = common._get_trial_recording_cache_path("evt-1")
    assert cache_path.exists()


@pytest.mark.unit
def test_load_trial_recording_uses_cached_npy_when_available(tmp_path, common):
    trial = tmp_path / "trial.npz"
    source_array = np.arange(24, dtype=np.uint16).reshape(2, 3, 4)
    np.savez_compressed(trial, arr_0=source_array)
    event = SimpleNamespace(event_id="evt-2", trial_npz_uri=trial.as_uri())
    common._trial_recording_cache_dir = tmp_path / "cache"

    first_loaded, first_err = common._load_trial_recording(event)
    assert first_err is None
    np.testing.assert_array_equal(first_loaded, source_array)

    trial.unlink()

    second_loaded, second_err = common._load_trial_recording(event)

    assert second_err is None
    np.testing.assert_array_equal(second_loaded, source_array)


@pytest.mark.unit
def test_load_trial_recording_rebuilds_cache_when_cache_file_is_missing(
    tmp_path, common
):
    trial = tmp_path / "trial.npz"
    array = np.arange(60, dtype=np.uint16).reshape(3, 4, 5)
    np.savez_compressed(trial, arr_0=array)
    event = SimpleNamespace(event_id="evt-3", trial_npz_uri=trial.as_uri())
    common._trial_recording_cache_dir = tmp_path / "cache"

    _, first_err = common._load_trial_recording(event)
    assert first_err is None

    cache_path = common._get_trial_recording_cache_path("evt-3")
    cache_path.unlink()

    loaded, err = common._load_trial_recording(event)

    assert err is None
    np.testing.assert_array_equal(loaded, array)
    assert cache_path.exists()


@pytest.mark.unit
def test_load_trial_recording_prunes_stale_cache_files(tmp_path, common):
    trial = tmp_path / "trial.npz"
    array = np.arange(24, dtype=np.uint16).reshape(2, 3, 4)
    np.savez_compressed(trial, arr_0=array)
    event = SimpleNamespace(event_id="evt-4", trial_npz_uri=trial.as_uri())
    common._trial_recording_cache_dir = tmp_path / "cache"

    stale_cache_path = common._get_trial_recording_cache_path("old-event")
    stale_cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(stale_cache_path, array, allow_pickle=False)
    old_mtime = time.time() - (common._trial_recording_cache_ttl_seconds + 60)
    os.utime(stale_cache_path, (old_mtime, old_mtime))

    loaded, err = common._load_trial_recording(event)

    assert err is None
    np.testing.assert_array_equal(loaded, array)
    assert not stale_cache_path.exists()


@pytest.mark.unit
def test_load_trial_recording_refreshes_cache_timestamp_on_access(tmp_path, common):
    trial = tmp_path / "trial.npz"
    array = np.arange(24, dtype=np.uint16).reshape(2, 3, 4)
    np.savez_compressed(trial, arr_0=array)
    event = SimpleNamespace(event_id="evt-5", trial_npz_uri=trial.as_uri())
    common._trial_recording_cache_dir = tmp_path / "cache"

    _, first_err = common._load_trial_recording(event)
    assert first_err is None

    cache_path = common._get_trial_recording_cache_path("evt-5")
    stale_mtime = time.time() - 60
    os.utime(cache_path, (stale_mtime, stale_mtime))

    loaded, err = common._load_trial_recording(event)

    assert err is None
    np.testing.assert_array_equal(loaded, array)
    assert cache_path.stat().st_mtime > stale_mtime
