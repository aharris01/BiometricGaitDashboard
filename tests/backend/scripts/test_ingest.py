import datetime
from pathlib import Path

import pytest

from backend.scripts.ingest import iter_swipes


def _create_event(
    root: Path,
    participant: int = 123,
    date_str: str = "2025-01-01",
    direction: str = "in",
    event_number: int = 1,
) -> Path:
    """Create a minimal swipe directory containing trial.npz."""
    event_dir = root / str(participant) / date_str / direction / str(event_number)
    event_dir.mkdir(parents=True, exist_ok=True)
    (event_dir / "trial.npz").touch()
    return event_dir


@pytest.mark.unit
def test_iter_swipes_yields_expected_fields(tmp_path):
    event_dir = _create_event(
        tmp_path,
        participant=111,
        date_str="2025-01-15",
        direction="in",
        event_number=5,
    )

    before = datetime.datetime.now()
    rows = list(iter_swipes(tmp_path))
    after = datetime.datetime.now()

    assert len(rows) == 1
    row = rows[0]
    assert row["event_id"] == "111_2025-01-15_in_5"
    assert row["root_path"] == event_dir.resolve().as_uri()
    assert row["present"] == 1
    assert isinstance(row["last_seen"], datetime.datetime)
    assert before <= row["last_seen"] <= after


@pytest.mark.unit
def test_iter_swipes_zero_pads_participant(tmp_path):
    event_dir = _create_event(
        tmp_path,
        participant=7,
        date_str="2025-12-31",
        direction="out",
        event_number=3,
    )

    rows = list(iter_swipes(tmp_path))
    assert len(rows) == 1
    row = rows[0]
    assert row["event_id"] == "007_2025-12-31_out_3"
    assert row["root_path"] == event_dir.resolve().as_uri()


@pytest.mark.unit
def test_iter_swipes_skips_malformed_paths(tmp_path, capfd):
    bad_dir = tmp_path / "not" / "enough" / "segments"
    bad_dir.mkdir(parents=True)
    (bad_dir / "trial.npz").touch()

    rows = list(iter_swipes(tmp_path))
    assert rows == []

    captured = capfd.readouterr()
    assert "error parsing swipe path" in captured.out


@pytest.mark.unit
def test_iter_swipes_handles_multiple_events(tmp_path):
    first_event = _create_event(
        tmp_path, participant=1, date_str="2024-05-01", direction="in", event_number=1
    )
    second_event = _create_event(
        tmp_path, participant=2, date_str="2024-05-02", direction="out", event_number=2
    )

    rows = sorted(iter_swipes(tmp_path), key=lambda r: r["event_id"])

    assert [r["event_id"] for r in rows] == [
        "001_2024-05-01_in_1",
        "002_2024-05-02_out_2",
    ]
    assert [r["root_path"] for r in rows] == [
        first_event.resolve().as_uri(),
        second_event.resolve().as_uri(),
    ]
