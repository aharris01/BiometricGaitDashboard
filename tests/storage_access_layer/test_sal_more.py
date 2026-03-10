from __future__ import annotations

import pytest
from io import BytesIO
from types import SimpleNamespace
from zipfile import ZIP_DEFLATED, ZipFile
from unittest.mock import MagicMock
import datetime as dt
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


# -------------------------------------------------------------------
# Review / create / delete / date helpers coverage expansion
# -------------------------------------------------------------------


@pytest.mark.unit
def test_get_trial_frame_count_ok(tmp_path, sal, fake_db):
    trial = tmp_path / "trial.npz"
    np.savez(trial, arr_0=np.zeros((7, 3, 2)))

    fake_db._event = SimpleNamespace(trial_npz_uri=trial.resolve().as_uri())

    frame_count, err = sal._get_trial_frame_count("evt-1")

    assert err is None
    assert frame_count == 7


@pytest.mark.unit
def test_get_trial_frame_count_missing_event(sal, fake_db):
    fake_db._event = None

    frame_count, err = sal._get_trial_frame_count("evt-1")

    assert frame_count is None
    assert err == "missing_event"


@pytest.mark.unit
def test_get_single_footstep_ok(sal, fake_db):
    fake_db._event = SimpleNamespace()
    fake_db.get_single_footstep = MagicMock(
        return_value=SimpleNamespace(
            footstep_id=4,
            start_frame=10,
            end_frame=20,
            x_min=1,
            x_max=11,
            y_min=2,
            y_max=12,
        )
    )

    out, err = sal.get_single_footstep("evt-1", 4)

    assert err is None
    assert out == {
        "id": 4,
        "start_frame": 10,
        "end_frame": 20,
        "x_min": 1,
        "x_max": 11,
        "y_min": 2,
        "y_max": 12,
    }


@pytest.mark.unit
def test_get_single_footstep_missing_file(sal, fake_db):
    fake_db._event = SimpleNamespace()
    fake_db.get_single_footstep = MagicMock(return_value=None)

    out, err = sal.get_single_footstep("evt-1", 4)

    assert out is None
    assert err == "missing_file"


@pytest.mark.unit
def test_get_footstep_review_context_ok(tmp_path, sal, fake_db):
    p100 = tmp_path / "trial.p100.npz"
    np.savez(p100, arr_0=np.array([[1.0, 2.0], [3.0, 4.0]]))

    fake_db._event = SimpleNamespace(trial_p100_npz_uri=p100.resolve().as_uri())
    fake_db.get_single_footstep = MagicMock(
        return_value=SimpleNamespace(
            footstep_id=5,
            start_frame=11,
            end_frame=22,
            x_min=1,
            x_max=9,
            y_min=2,
            y_max=10,
            label="left",
        )
    )
    fake_db.get_local_footstep_changes = MagicMock(
        return_value=[
            SimpleNamespace(
                action="edit",
                changed_at=dt.datetime(2026, 3, 10, 10, 30, 0),
                old_x_min=1,
                old_x_max=8,
                old_y_min=2,
                old_y_max=9,
                old_label="old",
                new_x_min=1,
                new_x_max=9,
                new_y_min=2,
                new_y_max=10,
                new_label="left",
            )
        ]
    )

    payload, err = sal.get_footstep_review_context("evt-1", 5)

    assert err is None
    assert payload["item"] == {
        "event_id": "evt-1",
        "footstep_id": 5,
        "start_frame": 11,
        "end_frame": 22,
        "label": "left",
    }
    assert payload["bbox"] == {
        "x_min": 1,
        "x_max": 9,
        "y_min": 2,
        "y_max": 10,
    }
    assert payload["image_width"] == 2
    assert payload["image_height"] == 2
    assert payload["event_p100"] == [[1.0, 2.0], [3.0, 4.0]]
    assert len(payload["changes"]) == 1
    assert payload["changes"][0]["action"] == "edit"
    assert payload["changes"][0]["old_label"] == "old"
    assert payload["changes"][0]["new_label"] == "left"


@pytest.mark.unit
def test_save_footstep_review_ok_with_label_normalization(sal, fake_db):
    fake_db.update_local_footstep = MagicMock(return_value=object())

    sal.get_footstep_review_context = MagicMock(
        side_effect=[
            (
                {
                    "image_width": 100,
                    "image_height": 80,
                },
                None,
            ),
            (
                {
                    "saved": True,
                },
                None,
            ),
        ]
    )

    out, err = sal.save_footstep_review(
        "evt-1",
        6,
        x_min=10,
        x_max=20,
        y_min=30,
        y_max=40,
        label="   ",
    )

    assert err is None
    assert out == {"saved": True}
    fake_db.update_local_footstep.assert_called_once_with(
        "evt-1",
        6,
        x_min=10,
        x_max=20,
        y_min=30,
        y_max=40,
        label=None,
    )


@pytest.mark.unit
def test_save_footstep_review_invalid_bbox_returns_error(sal):
    sal.get_footstep_review_context = MagicMock(
        return_value=(
            {
                "image_width": 100,
                "image_height": 80,
            },
            None,
        )
    )

    out, err = sal.save_footstep_review(
        "evt-1",
        6,
        x_min=-1,
        x_max=20,
        y_min=30,
        y_max=40,
        label="x",
    )

    assert out is None
    assert err == "invalid_bbox"


@pytest.mark.unit
def test_create_footstep_ok(tmp_path, sal, fake_db):
    fake_db._event = SimpleNamespace()
    fake_db.create_local_footstep = MagicMock(
        return_value=SimpleNamespace(footstep_id=12)
    )

    sal.get_p100 = MagicMock(return_value=[[1.0, 2.0], [3.0, 4.0]])
    sal._get_trial_frame_count = MagicMock(return_value=(50, None))
    sal.get_footstep_review_context = MagicMock(
        return_value=({"item": {"footstep_id": 12}}, None)
    )

    out, err = sal.create_footstep(
        "evt-1",
        start_frame=5,
        end_frame=10,
        x_min=1,
        x_max=2,
        y_min=0,
        y_max=2,
        label=" new ",
    )

    assert err is None
    assert out == {"item": {"footstep_id": 12}}
    fake_db.create_local_footstep.assert_called_once_with(
        "evt-1",
        start_frame=5,
        end_frame=10,
        x_min=1,
        x_max=2,
        y_min=0,
        y_max=2,
        label="new",
    )


@pytest.mark.unit
def test_create_footstep_invalid_frame_returns_error(sal, fake_db):
    fake_db._event = SimpleNamespace()
    sal.get_p100 = MagicMock(return_value=[[1.0, 2.0], [3.0, 4.0]])
    sal._get_trial_frame_count = MagicMock(return_value=(10, None))

    out, err = sal.create_footstep(
        "evt-1",
        start_frame=8,
        end_frame=8,
        x_min=1,
        x_max=2,
        y_min=0,
        y_max=2,
        label=None,
    )

    assert out is None
    assert err == "invalid_frame"


@pytest.mark.unit
def test_create_footstep_invalid_bbox_returns_error(sal, fake_db):
    fake_db._event = SimpleNamespace()
    sal.get_p100 = MagicMock(return_value=[[1.0, 2.0], [3.0, 4.0]])
    sal._get_trial_frame_count = MagicMock(return_value=(10, None))

    out, err = sal.create_footstep(
        "evt-1",
        start_frame=1,
        end_frame=2,
        x_min=2,
        x_max=1,
        y_min=0,
        y_max=2,
        label=None,
    )

    assert out is None
    assert err == "invalid_bbox"


@pytest.mark.unit
def test_delete_footstep_ok(sal, fake_db):
    fake_db._event = SimpleNamespace()
    fake_db.get_single_footstep = MagicMock(return_value=SimpleNamespace(footstep_id=7))
    fake_db.delete_local_footstep = MagicMock(return_value=True)

    out, err = sal.delete_footstep("evt-1", 7)

    assert err is None
    assert out == {
        "ok": True,
        "event_id": "evt-1",
        "footstep_id": 7,
    }


@pytest.mark.unit
def test_delete_footstep_missing_file(sal, fake_db):
    fake_db._event = SimpleNamespace()
    fake_db.get_single_footstep = MagicMock(return_value=None)

    out, err = sal.delete_footstep("evt-1", 7)

    assert out is None
    assert err == "missing_file"


@pytest.mark.unit
def test_get_all_footstep_details_ok(tmp_path, sal, fake_db):
    trial = tmp_path / "trial.npz"
    np.savez(trial, arr_0=np.zeros((2, 2)))

    steps_path = trial.with_name("steps.npz")
    _write_npz_with_numeric_keys(
        steps_path,
        {
            "2": np.array(
                [
                    [[1.0, 0.0], [0.0, 2.0]],
                    [[0.0, 3.0], [4.0, 0.0]],
                ]
            ),
            "1": np.array(
                [
                    [[1.0, 1.0], [1.0, 1.0]],
                    [[2.0, 2.0], [2.0, 2.0]],
                ]
            ),
        },
    )

    fake_db._event = SimpleNamespace(trial_npz_uri=trial.resolve().as_uri())

    items, err = sal.get_all_footstep_details("evt-1")

    assert err is None
    assert [item["id"] for item in items] == [1, 2]
    assert items[0]["p100"] == [[2.0, 2.0], [2.0, 2.0]]
    assert items[0]["grf"] == [4.0, 8.0]
    assert items[1]["p100"] == [[1.0, 3.0], [4.0, 2.0]]
    assert items[1]["grf"] == [3.0, 7.0]


@pytest.mark.unit
def test_get_date_bounds_ok_with_filters(sal, fake_db):
    fake_session = MagicMock()
    fake_session.execute.return_value.first.return_value = (
        dt.date(2025, 1, 1),
        dt.date(2025, 1, 31),
    )

    fake_db._get_session = MagicMock(
        return_value=MagicMock(
            __enter__=MagicMock(return_value=fake_session),
            __exit__=MagicMock(return_value=None),
        )
    )

    out = sal.get_date_bounds(filters={"participants": [1], "month": 1})

    assert out == {"min_date": "2025-01-01", "max_date": "2025-01-31"}


@pytest.mark.unit
def test_get_date_bounds_empty_returns_none_bounds(sal, fake_db):
    fake_session = MagicMock()
    fake_session.execute.return_value.first.return_value = (None, None)

    fake_db._get_session = MagicMock(
        return_value=MagicMock(
            __enter__=MagicMock(return_value=fake_session),
            __exit__=MagicMock(return_value=None),
        )
    )

    out = sal.get_date_bounds()

    assert out == {"min_date": None, "max_date": None}


@pytest.mark.unit
def test_get_distinct_date_values_ok(sal, fake_db):
    fake_session = MagicMock()
    fake_session.execute.return_value.all.return_value = [
        (3.0,),
        (1.0,),
        (None,),
        (2.0,),
        (1.0,),
    ]

    fake_db._get_session = MagicMock(
        return_value=MagicMock(
            __enter__=MagicMock(return_value=fake_session),
            __exit__=MagicMock(return_value=None),
        )
    )

    out = sal.get_distinct_date_values("month", filters={"year": 2025})

    assert out == [1, 2, 3]


@pytest.mark.unit
def test_get_distinct_date_values_invalid_part_raises(sal):
    with pytest.raises(ValueError):
        sal.get_distinct_date_values("hour")
