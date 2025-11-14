import os
from pathlib import Path

import numpy as np
import pytest

from backend.scripts.ingest import iter_swipes


def _make_event(root, participant=123, date_str="2025-01-01", direction="in", event_number=1, missing=None):
    event_dir = root / str(participant) / date_str / direction / str(event_number)
    event_dir.mkdir(parents=True, exist_ok=True)

    np.savez(event_dir / "trial.npz", arr=[1])
    missing = set(missing or [])
    if "p100" not in missing:
        np.savez(event_dir / "trial.p100.npz", arr=[2])
    if "grf" not in missing:
        np.savez(event_dir / "trial.grf.npz", arr=[3])

    return {
        "dir": event_dir,
        "trial": event_dir / "trial.npz",
        "p100": event_dir / "trial.p100.npz",
        "grf": event_dir / "trial.grf.npz",
        "participant": participant,
        "date": date_str,
        "direction": direction,
        "event": event_number,
    }


def test_iter_swipes_parses_valid_structure(tmp_path):
    event = _make_event(tmp_path, participant=111, date_str="2025-01-15", direction="in", event_number=5)

    rows = list(iter_swipes(tmp_path))
    assert len(rows) == 1
    row = rows[0]

    assert row["participant"] == 111
    assert row["date"].isoformat() == "2025-01-15"
    assert row["direction"] == "in"
    assert row["event_number"] == 5
    assert row["state"] == "ready"
    assert row["event_id"] == "111_2025-01-15_in_5_ready"
    assert row["trial_npz_uri"] == event["trial"].resolve().as_uri()
    assert row["trial_p100_npz_uri"] == event["p100"].resolve().as_uri()
    assert row["trial_grf_npz_uri"] == event["grf"].resolve().as_uri()


def test_iter_swipes_marks_failed_when_missing_files(tmp_path):
    event = _make_event(tmp_path, participant=222, date_str="2025-02-01", direction="out", event_number=7, missing={"grf"})

    rows = list(iter_swipes(tmp_path))
    assert len(rows) == 1
    row = rows[0]
    assert row["state"] == "failed"
    assert row["trial_grf_npz_uri"] == event["grf"].resolve().as_uri()


def test_iter_swipes_skips_malformed_paths(tmp_path, capfd):
    bad_dir = tmp_path / "not_enough" / "segments"
    bad_dir.mkdir(parents=True)
    np.savez(bad_dir / "trial.npz", arr=[0])

    rows = list(iter_swipes(tmp_path))
    assert rows == []

    captured = capfd.readouterr()
    assert "error parsing swipe path" in captured.out


def test_iter_swipes_handles_multiple_events(tmp_path):
    first = _make_event(tmp_path, participant=333, date_str="2025-03-01", direction="in", event_number=1)
    second = _make_event(tmp_path, participant=444, date_str="2025-03-02", direction="out", event_number=2)

    rows = sorted(iter_swipes(tmp_path), key=lambda r: r["event_id"])
    assert [row["participant"] for row in rows] == [333, 444]
    assert [row["event_number"] for row in rows] == [1, 2]
    assert [row["state"] for row in rows] == ["ready", "ready"]


def test_iter_swipes_relative_paths(tmp_path, monkeypatch):
    root = tmp_path / "nested" / "data"
    event = _make_event(root, participant=555, date_str="2025-04-05", direction="in", event_number=3)

    monkeypatch.chdir(tmp_path)
    rel_root = Path(os.path.relpath(root, start=tmp_path))

    rows = list(iter_swipes(rel_root))
    assert len(rows) == 1
    row = rows[0]
    assert row["trial_npz_uri"] == event["trial"].resolve().as_uri()
