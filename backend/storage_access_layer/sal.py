# backend/storage_access_layer/sal.py
from __future__ import annotations

import atexit
import csv
import os
from datetime import date
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple, cast

import numpy as np

from . import validators as v
from .db.db import DB

DATAROOT = Path(os.environ.get("DATAROOT", "."))


def event_base_path(event) -> Path:
    """
    Build the filesystem path to an event directory based on manifest fields.
    """
    return (
        DATAROOT
        / str(event.participant)
        / event.date.isoformat()
        / event.direction
        / str(event.event_number)
    )


class SAL:
    def __init__(self, db: DB | None = None):
        self.db = db or DB()
        atexit.register(self._close_db)

    def _close_db(self) -> None:
        if getattr(self, "db", None):
            close = getattr(self.db, "close", None)
            if close:
                close()

    # =========================================================
    # Meta lookups (snake_case)
    # =========================================================

    def get_participants(self) -> List[int]:
        raw = self.db.get_participants()
        result = cast(List[int], raw)
        v.get_participants_check(result)
        return result

    def get_dates(self, participant: int) -> List[date]:
        raw = self.db.get_dates(participant)
        result = cast(List[date], raw)
        v.get_dates_check(participant, result)
        return result

    def get_directions(self, participant: int, dt: date) -> List[Literal["in", "out"]]:
        raw = self.db.get_directions(participant, dt)
        result = cast(List[Literal["in", "out"]], raw)
        v.get_directions_check(participant, dt, result)
        return result

    def get_events(self, participant: int, dt: date, direction: str) -> List[int]:
        raw = self.db.get_events(participant, dt, direction)
        result = list(raw)
        v.get_events_check(participant, dt, direction, result)
        return result

    def get_swipe_event_id(
        self, participant: int, dt: date, event: int, direction: str
    ) -> Optional[str]:
        raw = self.db.get_swipe_event_id(participant, dt, event, direction)
        result: Optional[str] = None if raw is None else str(raw)
        v.get_swipe_event_id_check(participant, dt, event, direction, result)
        return result

    def get_both_direction_events(
        self, participant: int, dt: date
    ) -> Dict[str, List[int]]:
        result: Dict[str, List[int]] = {}
        directions = self.db.get_directions(participant, dt)
        for d in directions:
            events = cast(List[int], list(self.db.get_events(participant, dt, d)))
            result[d] = events
        v.get_both_direction_events_check(participant, dt, result)
        return result

    # =========================================================
    # Event data
    # =========================================================

    def get_event_summary(self, event_id: str) -> Optional[Tuple[dict, dict]]:
        """
        Return (event_dict, availability_dict) or None if event missing.
        """
        event = self.db.get_swipe_event(event_id)
        if event is None:
            return None

        base = event_base_path(event)

        event_dict = {
            "event_id": event.event_id,
            "participant": event.participant,
            "date": event.date.isoformat(),
            "direction": event.direction,
            "event_number": event.event_number,
        }

        availability = {
            "p100": (base / "trial.p100.npz").exists(),
            "grf": (base / "trial.grf.npz").exists(),
            "metadata": (base / "metadata.csv").exists(),
            "steps": (base / "steps.npz").exists(),
        }

        return event_dict, availability

    def get_p100(self, event_id: str):
        event = self.db.get_swipe_event(event_id)
        if event is None:
            return None

        path = event_base_path(event) / "trial.p100.npz"
        if not path.exists():
            return None

        try:
            data = np.load(path)
            return data["arr_0"].tolist()
        except Exception:
            return None

    def get_grf(self, event_id: str):
        event = self.db.get_swipe_event(event_id)
        if event is None:
            return None, "missing_event"

        path = event_base_path(event) / "trial.grf.npz"
        if not path.exists():
            return None, "missing_file"

        try:
            data = np.load(path)
            array = data[data.files[0]]
            return array.tolist(), None
        except Exception:
            return None, "missing_file"

    def get_footsteps(self, event_id: str):
        event = self.db.get_swipe_event(event_id)
        if event is None:
            return None, "missing_event"

        meta_path = event_base_path(event) / "metadata.csv"
        if not meta_path.exists():
            return None, "missing_file"

        try:
            with meta_path.open(newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception:
            return None, "missing_file"

        try:
            steps = [
                {
                    "id": int(row["FootstepID"]),
                    "start_frame": int(row["StartFrame"]),
                    "end_frame": int(row["EndFrame"]),
                    "x_min": int(row["XMin"]),
                    "x_max": int(row["XMax"]),
                    "y_min": int(row["YMin"]),
                    "y_max": int(row["YMax"]),
                }
                for row in rows
            ]
        except Exception:
            return None, "missing_file"

        return steps, None

    def get_footstep_data(self, event_id: str, step_id: int):
        event = self.db.get_swipe_event(event_id)
        if event is None:
            return None, None, "missing_event"

        steps_path = event_base_path(event) / "steps.npz"
        if not steps_path.exists():
            return None, None, "missing_file"

        try:
            steps_npz = np.load(steps_path)
            key = str(step_id)
            if key not in steps_npz.files:
                return None, None, "missing_file"

            vol = steps_npz[key]
            step_p100 = vol.max(axis=0)
            step_grf = vol.reshape(vol.shape[0], -1).sum(axis=1)
            return step_p100.tolist(), step_grf.tolist(), None
        except Exception:
            return None, None, "missing_file"

    def get_all_footstep_p100(self, event_id: str):
        event = self.db.get_swipe_event(event_id)
        if event is None:
            return None, "missing_event"

        steps_path = event_base_path(event) / "steps.npz"
        if not steps_path.exists():
            return None, "missing_file"

        try:
            steps_npz = np.load(steps_path)
            items = [
                {
                    "id": int(k),
                    "p100": steps_npz[k].max(axis=0).tolist(),
                }
                for k in steps_npz.files
            ]
            items.sort(key=lambda x: x["id"])
            return items, None
        except Exception:
            return None, "missing_file"

    def get_all_footstep_details(self, event_id: str):
        event = self.db.get_swipe_event(event_id)
        if event is None:
            return None, "missing_event"

        steps_path = event_base_path(event) / "steps.npz"
        if not steps_path.exists():
            return None, "missing_file"

        try:
            steps_npz = np.load(steps_path)
            items = []
            for k in steps_npz.files:
                vol = steps_npz[k]
                items.append(
                    {
                        "id": int(k),
                        "p100": vol.max(axis=0).tolist(),
                        "grf": vol.reshape(vol.shape[0], -1).sum(axis=1).tolist(),
                    }
                )
            items.sort(key=lambda x: x["id"])
            return items, None
        except Exception:
            return None, "missing_file"

    # =========================================================
    # Backward-compatible camelCase wrappers
    # =========================================================

    def getParticipants(self):
        return self.get_participants()

    def getDates(self, participant):
        return self.get_dates(participant)

    def getDirections(self, participant, dt):
        return self.get_directions(participant, dt)

    def getEvents(self, participant, dt, direction):
        return self.get_events(participant, dt, direction)

    def getSwipeEventId(self, participant, dt, event, direction):
        return self.get_swipe_event_id(participant, dt, event, direction)

    def getBothDirectionEvents(self, participant, dt):
        return self.get_both_direction_events(participant, dt)

    def getEventSummary(self, event_id):
        return self.get_event_summary(event_id)

    def getP100(self, event_id):
        return self.get_p100(event_id)

    def getGRF(self, event_id):
        return self.get_grf(event_id)

    def getFootsteps(self, event_id):
        return self.get_footsteps(event_id)

    def getFootstepData(self, event_id, step_id):
        return self.get_footstep_data(event_id, step_id)

    def getAllFootstepP100(self, event_id):
        return self.get_all_footstep_p100(event_id)

    def getAllFootstepDetails(self, event_id):
        return self.get_all_footstep_details(event_id)
