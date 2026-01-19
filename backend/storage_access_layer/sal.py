# backend/storage_access_layer/sal.py
from __future__ import annotations

import atexit
import csv
import os
from datetime import date
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple, cast
from urllib.parse import unquote, urlparse

import numpy as np

from . import validators as v
from .db.db import DB


def uri_to_path(uri: str) -> Path:
    """
    Convert a file:// URI (stored in the DB) to a real filesystem Path,
    working on both Windows and Unix-like systems.
    """
    parsed = urlparse(str(uri))

    if parsed.scheme != "file":
        raise ValueError(f"Unsupported URI scheme in {uri!r}; expected file://")

    path = unquote(parsed.path)

    # On Windows, parsed.path often starts with "/C:/..."
    if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
        path = path[1:]

    return Path(path)


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
    # Event data (snake_case)
    # =========================================================

    def get_event_summary(self, event_id: str) -> Optional[Tuple[dict, dict]]:
        """
        Return (event_dict, availability_dict) or None if event missing.

        availability includes whether p100/grf/metadata/steps exist on disk.
        """
        event = self.db.get_swipe_event(event_id)
        if event is None:
            return None

        event_dict = {
            "event_id": event.event_id,
            "participant": event.participant,
            "date": event.date.isoformat() if getattr(event, "date", None) else None,
            "direction": event.direction,
            "event_number": event.event_number,
        }

        availability: dict = {}

        # p100 availability
        try:
            p100_path = uri_to_path(event.trial_p100_npz_uri)
            availability["p100"] = p100_path.exists()
        except Exception:
            availability["p100"] = False

        # grf availability
        try:
            grf_path = uri_to_path(event.trial_grf_npz_uri)
            availability["grf"] = grf_path.exists()
        except Exception:
            availability["grf"] = False

        # metadata.csv and steps.npz live next to trial_npz_uri
        try:
            trial_path = uri_to_path(event.trial_npz_uri)
            availability["metadata"] = trial_path.with_name("metadata.csv").exists()
            availability["steps"] = trial_path.with_name("steps.npz").exists()
        except Exception:
            availability["metadata"] = False
            availability["steps"] = False

        return event_dict, availability

    def get_p100(self, event_id: str):
        """
        Return P100 as a JSON-serialisable list (2D array), or None if missing.
        """
        event = self.db.get_swipe_event(event_id)
        if event is None:
            return None

        try:
            file_path = uri_to_path(event.trial_p100_npz_uri)
        except ValueError:
            return None

        try:
            loaded_file = np.load(file_path)
        except FileNotFoundError:
            return None

        array = loaded_file["arr_0"]
        return array.tolist()

    def get_grf(self, event_id: str):
        """
        Returns:
            (data_list, None) on success
            (None, "missing_event") if event not in DB
            (None, "missing_file")  if GRF file missing/unreadable
        """
        event = self.db.get_swipe_event(event_id)
        if event is None:
            return None, "missing_event"

        try:
            file_path = uri_to_path(event.trial_grf_npz_uri)
        except ValueError:
            return None, "missing_file"

        try:
            loaded = np.load(file_path)
        except FileNotFoundError:
            return None, "missing_file"
        except Exception:
            return None, "missing_file"

        try:
            if hasattr(loaded, "files") and "arr_0" in loaded.files:
                array = loaded["arr_0"]
            elif hasattr(loaded, "files") and loaded.files:
                array = loaded[loaded.files[0]]
            else:
                array = loaded
        except Exception:
            return None, "missing_file"

        try:
            data_list = array.tolist()
        except Exception:
            return None, "missing_file"

        return data_list, None

    def get_footsteps(self, event_id: str):
        """
        Load per-footstep metadata from metadata.csv (next to trial.npz).

        Returns:
            (steps, None) on success
            (None, "missing_event") if DB record missing
            (None, "missing_file")  if file missing/unreadable
        """
        event = self.db.get_swipe_event(event_id)
        if event is None:
            return None, "missing_event"

        try:
            trial_path = uri_to_path(event.trial_npz_uri)
        except ValueError:
            return None, "missing_file"

        meta_path = trial_path.with_name("metadata.csv")
        if not meta_path.exists():
            return None, "missing_file"

        try:
            with meta_path.open(newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception:
            return None, "missing_file"

        steps: list[dict] = []
        try:
            for row in rows:
                steps.append(
                    {
                        "id": int(row["FootstepID"]),
                        "start_frame": int(row["StartFrame"]),
                        "end_frame": int(row["EndFrame"]),
                        "x_min": int(row["XMin"]),
                        "x_max": int(row["XMax"]),
                        "y_min": int(row["YMin"]),
                        "y_max": int(row["YMax"]),
                    }
                )
        except (KeyError, ValueError):
            return None, "missing_file"

        return steps, None

    def get_footstep_data(self, event_id: str, step_id: int):
        """
        Load a single footstep volume from steps.npz and return:
          - step_p100: 2D max image for this step
          - step_grf:  1D curve for this step
        """
        event = self.db.get_swipe_event(event_id)
        if event is None:
            return None, None, "missing_event"

        try:
            trial_path = uri_to_path(event.trial_npz_uri)
        except ValueError:
            return None, None, "missing_file"

        steps_path = trial_path.with_name("steps.npz")
        if not steps_path.exists():
            return None, None, "missing_file"

        try:
            steps_npz = np.load(steps_path)
        except Exception:
            return None, None, "missing_file"

        key = str(step_id)
        if key not in steps_npz.files:
            return None, None, "missing_file"

        vol = steps_npz[key]  # (T, H, W)

        step_p100 = vol.max(axis=0)  # (H, W)
        step_grf = vol.reshape(vol.shape[0], -1).sum(axis=1)  # (T,)

        return step_p100.tolist(), step_grf.tolist(), None

    def get_all_footstep_p100(self, event_id: str):
        """
        Load ALL footstep P100 images from steps.npz (one disk read).
        Returns:
            (items, None) on success where items = [{"id": int, "p100": [[...]]}, ...]
            (None, "missing_event") if event missing
            (None, "missing_file") if steps.npz missing/unreadable
        """
        event = self.db.get_swipe_event(event_id)
        if event is None:
            return None, "missing_event"

        try:
            trial_path = uri_to_path(event.trial_npz_uri)
        except ValueError:
            return None, "missing_file"

        steps_path = trial_path.with_name("steps.npz")
        if not steps_path.exists():
            return None, "missing_file"

        try:
            steps_npz = np.load(steps_path)
        except Exception:
            return None, "missing_file"

        items = []
        try:
            for key in steps_npz.files:
                vol = steps_npz[key]  # (T, H, W)
                step_p100 = vol.max(axis=0)  # (H, W)
                items.append({"id": int(key), "p100": step_p100.tolist()})
        except Exception:
            return None, "missing_file"

        items.sort(key=lambda x: x["id"])
        return items, None

    # return all footstep thumbnails + per-step GRF in one call
    def get_all_footstep_details(self, event_id: str):
        """
        Load ALL footstep details from steps.npz (one disk read).
        Returns:
            (items, None) on success where items = [{"id": int, "p100": [[...]], "grf": [...]}, ...]
            (None, "missing_event") if event missing
            (None, "missing_file") if steps.npz missing/unreadable
        """
        event = self.db.get_swipe_event(event_id)
        if event is None:
            return None, "missing_event"

        try:
            trial_path = uri_to_path(event.trial_npz_uri)
        except ValueError:
            return None, "missing_file"

        steps_path = trial_path.with_name("steps.npz")
        if not steps_path.exists():
            return None, "missing_file"

        try:
            steps_npz = np.load(steps_path)
        except Exception:
            return None, "missing_file"

        items = []
        try:
            for key in steps_npz.files:
                vol = steps_npz[key]  # (T, H, W)
                step_p100 = vol.max(axis=0)  # (H, W)
                step_grf = vol.reshape(vol.shape[0], -1).sum(axis=1)  # (T,)
                items.append(
                    {
                        "id": int(key),
                        "p100": step_p100.tolist(),
                        "grf": step_grf.tolist(),
                    }
                )
        except Exception:
            return None, "missing_file"

        items.sort(key=lambda x: x["id"])
        return items, None

    # =========================================================
    # Backward-compatible wrappers (camelCase)
    # =========================================================

    def getParticipants(self) -> List[int]:
        return self.get_participants()

    def getDates(self, participant: int) -> List[date]:
        return self.get_dates(participant)

    def getDirections(self, participant: int, dt: date):
        return self.get_directions(participant, dt)

    def getEvents(self, participant: int, dt: date, direction: str) -> List[int]:
        return self.get_events(participant, dt, direction)

    def getSwipeEventId(
        self, participant: int, dt: date, event: int, direction: str
    ) -> Optional[str]:
        return self.get_swipe_event_id(participant, dt, event, direction)

    def getBothDirectionEvents(
        self, participant: int, dt: date
    ) -> Dict[str, List[int]]:
        return self.get_both_direction_events(participant, dt)

    def getEventSummary(self, event_id: str):
        return self.get_event_summary(event_id)

    def getP100(self, event_id: str):
        return self.get_p100(event_id)

    def getGRF(self, event_id: str):
        return self.get_grf(event_id)

    def getFootsteps(self, event_id: str):
        return self.get_footsteps(event_id)

    def getFootstepData(self, event_id: str, step_id: int):
        return self.get_footstep_data(event_id, step_id)

    def getAllFootstepP100(self, event_id: str):
        return self.get_all_footstep_p100(event_id)

    def getAllFootstepDetails(self, event_id: str):
        return self.get_all_footstep_details(event_id)
