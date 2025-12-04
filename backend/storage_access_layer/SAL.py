from datetime import date
from typing import Dict, List, Literal, cast, Optional

import os
from pathlib import Path
from urllib.parse import urlparse, unquote

import csv
import numpy as np

from .db import DB
from . import validators as v
import atexit


def uri_to_path(uri: str) -> Path:
    """
    Convert a file:// URI (stored in the DB) to a real filesystem Path,
    working on both Windows and Unix-like systems.
    """
    parsed = urlparse(str(uri))

    if parsed.scheme != "file":
        raise ValueError(f"Unsupported URI scheme in {uri!r}; expected file://")

    # Decode URL-escaped characters and get the path part
    path = unquote(parsed.path)  # e.g. "/Users/me/..." or "/C:/Users/me/..."

    # On Windows, parsed.path often starts with "/C:/..."
    if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
        # drop leading "/" → "C:/Users/me/..."
        path = path[1:]

    return Path(path)


class SAL:
    # =========================================================
    # Backend ↔ SAL to get data by event_id primary key
    # =========================================================

    def __init__(self, db=None):
        self.db = db or DB()
        atexit.register(self._close_db)

    def _close_db(self):
        if getattr(self, "db", None):
            close = getattr(self.db, "close", None)
            if close:
                close()

    # -------------------- Meta lookups -------------------- #

    def getParticipants(self) -> List[int]:
        raw = self.db.getParticipants()
        result = cast(List[int], raw)
        v.getParticipants_check(result)
        return result

    def getDates(self, participant: int) -> List[date]:
        raw = self.db.getDates(participant)
        result = cast(List[date], raw)
        v.getDates_check(participant, result)
        return result

    def getDirections(self, participant: int, dt: date) -> List[Literal["in", "out"]]:
        raw = self.db.getDirections(participant, dt)
        result = cast(List[Literal["in", "out"]], raw)
        v.getDirections_check(participant, dt, result)
        return result

    def getEvents(self, participant: int, dt: date, direction: str) -> List[int]:
        raw = self.db.getEvents(participant, dt, direction)
        result = list(raw)
        v.getEvents_check(participant, dt, direction, result)
        return result

    def getSwipeEventId(
        self, participant: int, dt: date, event: int, direction: str
    ) -> Optional[str]:
        """
        Return the event_id string for a given swipe, or None if not found.
        """
        raw = self.db.getSwipeEventId(participant, dt, event, direction)
        # Keep None as None instead of turning it into the string "None"
        result: Optional[str] = None if raw is None else str(raw)
        v.getSwipeEventId_check(participant, dt, event, direction, result)
        return result

    def getBothDirectionEvents(
        self, participant: int, dt: date
    ) -> Dict[str, List[int]]:
        result: Dict[str, List[int]] = {}
        directions = self.db.getDirections(participant, dt)
        for d in directions:
            events = cast(List[int], list(self.db.getEvents(participant, dt, d)))
            result[d] = events
        v.getBothDirectionEvents_check(participant, dt, result)
        return result

    # -------------------- Event data -------------------- #

    def getEventSummary(self, event_id: str):
        raise NotImplementedError

    def getP100(self, event_id: str):
        """
        Return P100 as a JSON-serialisable list (2D array), or None if
        event/file is missing. server.py treats None as "no data".
        """
        event = self.db.getSwipeEvent(event_id)
        if event is None:
            return None

        try:
            file_path = uri_to_path(event.trial_p100_npz_uri)
        except ValueError:
            return None

        try:
            loaded_file = np.load(file_path)
        except FileNotFoundError:
            # File missing on disk
            return None

        array = loaded_file["arr_0"]
        return array.tolist()

    def getGRF(self, event_id: str):
        """
        Load GRF data for a given event.

        Returns:
            (data_list, None) on success
            (None, "missing_event") if event not in DB
            (None, "missing_file")  if GRF file missing or unreadable
        """
        event = self.db.getSwipeEvent(event_id)
        if event is None:
            return None, "missing_event"

        # Convert file:// URI to local path
        try:
            file_path = uri_to_path(event.trial_grf_npz_uri)
        except ValueError:
            # URI isn't a proper file://
            return None, "missing_file"

        # Try loading the .npz file
        try:
            loaded = np.load(file_path)
        except FileNotFoundError:
            return None, "missing_file"
        except Exception:
            # Any other numpy/file-related error
            return None, "missing_file"

        # Try to extract an array from the npz safely
        try:
            # Most np.savez files store the main array as "arr_0"
            if hasattr(loaded, "files") and "arr_0" in loaded.files:
                array = loaded["arr_0"]
            elif hasattr(loaded, "files") and loaded.files:
                # Fallback: take the first array in the container
                first_key = loaded.files[0]
                array = loaded[first_key]
            else:
                # Not a standard npz container (maybe already a plain array)
                array = loaded
        except Exception:
            return None, "missing_file"

        # Finally, make sure it's JSON-serialisable
        try:
            data_list = array.tolist()
        except Exception:
            return None, "missing_file"

        return data_list, None

    def getFootsteps(self, event_id):
        """
        Load per-footstep metadata for this trial.

        Returns:
            (steps, None) on success, where steps is a list of dicts:
                {
                  "id": int,
                  "start_frame": int,
                  "end_frame": int,
                  "x_min": int,
                  "x_max": int,
                  "y_min": int,
                  "y_max": int,
                }

            (None, "missing_event") if the DB record is missing
            (None, "missing_file")  if the metadata file is missing/unreadable
        """
        event = self.db.getSwipeEvent(event_id)
        if event is None:
            return None, "missing_event"

        # trial.npz URI → local Path
        try:
            trial_path = uri_to_path(event.trial_npz_uri)
        except ValueError:
            return None, "missing_file"

        # Your data uses "metadata.csv" in the same folder as trial.npz
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
            # Bad or missing columns / values
            return None, "missing_file"

        return steps, None

    def getFootstepData(self, event_id: str, step_id: int):
        """
        Load a single footstep volume from steps.npz and return:
          - step_p100: 2D image (P100-style) for this step
          - step_grf:  1D GRF curve for this step
        """
        event = self.db.getSwipeEvent(event_id)
        if event is None:
            return None, None, "missing_event"

        try:
            trial_path = uri_to_path(event.trial_npz_uri)
        except ValueError:
            return None, None, "missing_file"

        # Your data uses "steps.npz" in the same folder as trial.npz
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

        vol = steps_npz[key]  # shape: (T, H, W)

        # P100-style image for this step
        step_p100 = vol.max(axis=0)  # (H, W)

        # GRF for this step
        step_grf = vol.reshape(vol.shape[0], -1).sum(axis=1)  # (T,)

        return step_p100.tolist(), step_grf.tolist(), None
