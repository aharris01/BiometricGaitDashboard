import datetime
from datetime import date
from pathlib import Path


def iter_swipes(root: Path):
    for swipe in root.rglob("trial.npz"):
        swipe_parts = swipe.parts
        try:
            participant = int(swipe_parts[-5])
            event_date = date.fromisoformat(swipe_parts[-4])
            direction = str(swipe_parts[-3])
            event_number = int(swipe_parts[-2])
            event_dir = Path(*swipe_parts[:-1])
        except Exception:
            # Skip files that do not follow the expected directory layout
            print(f"error parsing swipe path: {swipe}")
            continue

        event_id = f"{participant:03d}_{event_date}_{direction}_{event_number}"
        yield {
            "event_id": event_id,
            "root_path": event_dir.resolve().as_uri(),
            "present": 1,
            "last_seen": datetime.datetime.now(),
        }
