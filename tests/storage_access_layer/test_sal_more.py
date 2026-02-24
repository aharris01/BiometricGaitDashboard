from __future__ import annotations

import pytest
from io import BytesIO
from types import SimpleNamespace
from zipfile import ZIP_DEFLATED, ZipFile
from unittest.mock import MagicMock

import numpy as np

from backend.storage_access_layer.sal import SAL


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def _write_npz_with_numeric_keys(path, arrays: dict[str, np.ndarray]) -> None:
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
    class DBStub:
        def __init__(self):
            self._event = None

        def get_swipe_event(self, event_id):
            return self._event

        def get_available_metrics(self):
            return []

        def get_distinct_date_part(self, part):
            return []

        def _get_session(self):
            raise NotImplementedError

        def close(self):
            pass

    return DBStub()


@pytest.fixture
def sal(fake_db):
    return SAL(db=fake_db)


# -------------------------------------------------------------------
# File / NPZ edge cases
# -------------------------------------------------------------------


@pytest.mark.unit
def test_get_p100_invalid_uri_returns_none(sal, fake_db):
    fake_db._event = SimpleNamespace(trial_p100_npz_uri="http://example.com/p100.npz")
    out = sal.get_p100("evt-1")
    assert out is None


@pytest.mark.unit
def test_get_grf_reads_non_arr0_first_key(tmp_path, sal, fake_db):
    p = tmp_path / "grf.npz"
    np.savez(p, foo=np.array([1.0, 2.0, 3.0]))

    fake_db._event = SimpleNamespace(trial_grf_npz_uri=p.resolve().as_uri())
    data, err = sal.get_grf("evt-1")
    assert err is None
    assert data == [1.0, 2.0, 3.0]


@pytest.mark.unit
def test_get_footsteps_bad_csv_returns_missing_file(tmp_path, sal, fake_db):
    trial = tmp_path / "trial.npz"
    np.savez(trial, arr_0=np.zeros((2, 2)))

    meta = trial.with_name("metadata.csv")
    meta.write_text("FootstepID,StartFrame\n0,10\n")

    fake_db._event = SimpleNamespace(trial_npz_uri=trial.resolve().as_uri())
    steps, err = sal.get_footsteps("evt-1")
    assert steps is None
    assert err == "missing_file"


@pytest.mark.unit
def test_get_footstep_data_missing_step_key(tmp_path, sal, fake_db):
    trial = tmp_path / "trial.npz"
    np.savez(trial, arr_0=np.zeros((2, 2)))

    steps_path = trial.with_name("steps.npz")
    _write_npz_with_numeric_keys(steps_path, {"1": np.ones((2, 2, 2))})

    fake_db._event = SimpleNamespace(trial_npz_uri=trial.resolve().as_uri())
    p100, grf, err = sal.get_footstep_data("evt-1", 0)
    assert p100 is None and grf is None
    assert err == "missing_file"


@pytest.mark.unit
def test_get_all_footstep_details_missing_file(tmp_path, sal, fake_db):
    trial = tmp_path / "trial.npz"
    np.savez(trial, arr_0=np.zeros((2, 2)))

    fake_db._event = SimpleNamespace(trial_npz_uri=trial.resolve().as_uri())
    items, err = sal.get_all_footstep_details("evt-1")
    assert items is None
    assert err == "missing_file"


# -------------------------------------------------------------------
# Summary plot coverage expansion
# -------------------------------------------------------------------


@pytest.mark.unit
def test_summary_plot_invalid_metric_raises(sal):
    sal.get_available_metrics = MagicMock(return_value=["valid_metric"])

    with pytest.raises(ValueError):
        sal.get_swipe_event_summary_plot_data(
            x="invalid_metric",
            y="valid_metric",
        )


@pytest.mark.unit
def test_summary_plot_empty_db_result(sal, fake_db):
    sal.get_available_metrics = MagicMock(return_value=["avg_bbox_size", "step_count"])

    fake_session = MagicMock()
    fake_session.execute.return_value.all.return_value = []

    fake_db._get_session = MagicMock(
        return_value=MagicMock(
            __enter__=MagicMock(return_value=fake_session),
            __exit__=MagicMock(return_value=None),
        )
    )

    out = sal.get_swipe_event_summary_plot_data(
        x="avg_bbox_size",
        y="step_count",
    )

    assert out == {}


@pytest.mark.unit
def test_summary_plot_multiple_rows_and_partial_metrics(sal, fake_db):
    sal.get_available_metrics = MagicMock(return_value=["avg_bbox_size", "step_count"])

    fake_session = MagicMock()
    fake_session.execute.return_value.all.return_value = [
        {"event_id": "E1", "avg_bbox_size": 10, "step_count": 5},
        {"event_id": "E2", "avg_bbox_size": None, "step_count": 7},
        {"event_id": "E3", "avg_bbox_size": 3, "step_count": None},
        {"event_id": None, "avg_bbox_size": 9, "step_count": 9},
    ]

    fake_db._get_session = MagicMock(
        return_value=MagicMock(
            __enter__=MagicMock(return_value=fake_session),
            __exit__=MagicMock(return_value=None),
        )
    )

    out = sal.get_swipe_event_summary_plot_data(
        "avg_bbox_size",
        "step_count",
    )

    assert "E1" in out
    assert "E2" in out
    assert "E3" in out
    assert None in out


@pytest.mark.unit
def test_summary_plot_all_filters_applied(sal, fake_db):
    sal.get_available_metrics = MagicMock(return_value=["avg_bbox_size", "step_count"])

    fake_session = MagicMock()
    fake_session.execute.return_value.all.return_value = [
        {"event_id": "E100", "avg_bbox_size": 1, "step_count": 2}
    ]

    fake_db._get_session = MagicMock(
        return_value=MagicMock(
            __enter__=MagicMock(return_value=fake_session),
            __exit__=MagicMock(return_value=None),
        )
    )

    out = sal.get_swipe_event_summary_plot_data(
        "avg_bbox_size",
        "step_count",
        filters={
            "participants": [1, 2],
            "year": 2024,
            "month": 5,
            "day": 10,
        },
    )

    assert out == {
        "E100": {
            "avg_bbox_size": 1,
            "step_count": 2,
        }
    }


@pytest.mark.unit
def test_summary_plot_row_missing_both_metrics(sal, fake_db):
    sal.get_available_metrics = MagicMock(return_value=["avg_bbox_size", "step_count"])

    fake_session = MagicMock()
    fake_session.execute.return_value.all.return_value = [
        {"event_id": "E1", "avg_bbox_size": None, "step_count": None}
    ]

    fake_db._get_session = MagicMock(
        return_value=MagicMock(
            __enter__=MagicMock(return_value=fake_session),
            __exit__=MagicMock(return_value=None),
        )
    )

    out = sal.get_swipe_event_summary_plot_data(
        "avg_bbox_size",
        "step_count",
    )

    assert "E1" in out
    assert out["E1"]["avg_bbox_size"] is None
    assert out["E1"]["step_count"] is None
