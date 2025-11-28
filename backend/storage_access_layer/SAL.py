from datetime import date
from typing import Dict, List, Literal, cast, Optional

import os
from pathlib import Path
from urllib.parse import urlparse, unquote

import numpy as np
import pandas as pd

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

    def getBothDirectionEvents(self, participant: int, dt: date) -> Dict[str, List[int]]:
        result: Dict[str, List[int]] = {}
        directions = self.db.getDirections(participant, dt)
        for d in directions:
            result[d] = self.db.getEvents(participant, dt, d)
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

    def getFootsteps(self, event_id: str):
        """
        Return one bounding box per footstep for this event, based on
        metadata CSV (and basic pressure metrics inside each box).

        Expects a metadata.csv in the same folder as trial P100 file,
        with at least columns: XMin, XMax, YMin, YMax.

        Returns:
            ([footstep_dict, ...], None) on success
            (None, "missing_event")  if no such event
            (None, "missing_file")   if files/metadata missing or invalid
        """
        event = self.db.getSwipeEvent(event_id)
        if event is None:
            return None, "missing_event"

        # 1. Locate P100 file and metadata.csv
        try:
            p100_path = uri_to_path(event.trial_p100_npz_uri)
        except ValueError:
            return None, "missing_file"

        event_dir = p100_path.parent            # folder for this trial
        metadata_path = event_dir / "metadata.csv"

        if not metadata_path.exists():
            # No metadata → we can't know individual steps
            return None, "missing_file"

        try:
            p100_loaded = np.load(p100_path)
            p100 = p100_loaded["arr_0"]
        except Exception:
            return None, "missing_file"

        try:
            df = pd.read_csv(metadata_path)
        except Exception:
            return None, "missing_file"

        # Require notebook-style columns
        required_cols = {"XMin", "XMax", "YMin", "YMax"}
        if not required_cols.issubset(df.columns):
            return None, "missing_file"

        footsteps = []

        # 2. One bounding box per row in metadata.csv
        for idx, row in df.iterrows():
            x_min = int(row["XMin"])
            x_max = int(row["XMax"])
            y_min = int(row["YMin"])
            y_max = int(row["YMax"])

            # Clamp to P100 array bounds, just in case
            h, w = p100.shape[:2]
            x_min = max(0, min(x_min, w - 1))
            x_max = max(0, min(x_max, w - 1))
            y_min = max(0, min(y_min, h - 1))
            y_max = max(0, min(y_max, h - 1))

            if x_max < x_min or y_max < y_min:
                # Bad box – skip
                continue

            # Slice region inside this box
            region = p100[y_min : y_max + 1, x_min : x_max + 1]
            active = region[region > 0]

            if active.size == 0:
                area_px = 0
                peak_pressure = 0.0
                mean_pressure = 0.0
            else:
                area_px = int(active.size)
                peak_pressure = float(active.max())
                mean_pressure = float(active.mean())

            footsteps.append(
                {
                    "id": int(idx) + 1,   # 1-based step ID
                    "x_min": x_min,
                    "x_max": x_max,
                    "y_min": y_min,
                    "y_max": y_max,
                    "area_px": area_px,
                    "peak_pressure": peak_pressure,
                    "mean_pressure": mean_pressure,
                }
            )

        return footsteps, None
