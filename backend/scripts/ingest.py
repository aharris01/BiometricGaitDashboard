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
            print("error")

        trial_p100 = event_dir / "trial.p100.npz"
        trial_grf = event_dir / "trial.grf.npz"

        if all(f.exists() for f in [trial_p100, trial_grf]):
            state = "ready"
        else:
            state = "failed"

        event_id = f"{participant:03d}_{event_date}_{direction}_{event_number}_{state}"
        yield {
            "event_id": event_id,
            "participant": participant,
            "date": event_date,
            "direction": direction,
            "event_number": event_number,
            "state": state,
            "trial_npz_uri": swipe.resolve().as_uri(),
            "trial_p100_npz_uri": trial_p100.resolve().as_uri(),
            "trial_grf_npz_uri": trial_grf.resolve().as_uri(),
        }
