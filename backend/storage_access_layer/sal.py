# backend/storage_access_layer/sal.py
from __future__ import annotations

import atexit
import csv
import os
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple, cast
from urllib.parse import unquote, urlparse

import numpy as np

from . import validators as v
from .db.db import DB

DATAROOT = Path(os.environ.get("dataroot", "."))  # Defaults to root
# Lowercase alias so tests can monkeypatch `sal_mod.dataroot`
dataroot = DATAROOT


def uri_to_path(uri: str) -> Path:
    """
    Convert a file:// URI (stored in the DB) to a real filesystem Path,
    working on both Windows and Unix-like systems.
    """
    parsed = urlparse(str(uri))

    if parsed.scheme != "file":
        raise ValueError(f"Unsupported URI scheme in {uri!r}; expected file://")

    path = unquote(parsed.path)  # e.g. "/Users/me/..." or "/C:/Users/me/..."

    if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
        path = path[1:]

    return Path(path)


class SAL:
    # =========================================================
    # Backend ↔ SAL to get data by event_id primary key
    # =========================================================

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

        date_value = event.date
        if isinstance(date_value, (datetime, date)):
            date_value = date_value.isoformat()

        event_dict = {
            "event_id": event.event_id,
            "participant": event.participant,
            "date": date_value,
            "direction": event.direction,
            "event_number": event.event_number,
        }

        availability: dict = {}

        try:
            p100_path = uri_to_path(event.trial_p100_npz_uri)
            availability["p100"] = p100_path.exists()
        except Exception:
            availability["p100"] = False

        try:
            grf_path = uri_to_path(event.trial_grf_npz_uri)
            availability["grf"] = grf_path.exists()
        except Exception:
            availability["grf"] = False

        try:
            trial_path = uri_to_path(event.trial_npz_uri)
            availability["metadata"] = trial_path.with_name("metadata.csv").exists()
            availability["steps"] = trial_path.with_name("steps.npz").exists()
        except Exception:
            availability["metadata"] = False
            availability["steps"] = False

        return event_dict, availability

    def get_p100(self, event_id: str):
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

    def get_all_footstep_details(self, event_id: str):
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

    # accessor function for average bounding box size of a specific event
    def get_average_bounding_box_size(self, event_id: str) -> Optional[float]:
        event = self.db.get_swipe_event(event_id)
        if event is None:
            return None

    # =========================================================
    # Summary plot helpers
    # =========================================================
    def get_event_id_from_URI(self, file_path: str) -> Optional[str]:
        """
        Extract participant/date/direction/event from a metadata.csv path and
        resolve it to the DB event_id.

        Supports both Windows-style paths (data\\100\\...) and Unix-style (data/100/...).
        """
        # Normalize Windows separators so this works on macOS/Linux too (and in unit tests)
        normalized = str(file_path).replace("\\", "/")
        p = Path(normalized)

        # Make relative to dataroot if possible
        try:
            rel = p.relative_to(dataroot)
            parts = rel.parts
        except ValueError:
            parts = p.parts

        # Handle when dataroot="." and full path includes ".../data/<...>"
        if "data" in parts:
            parts = parts[parts.index("data") + 1 :]

        # Expect: participant/date/direction/event/metadata.csv
        if len(parts) < 5:
            return None

        participant = parts[0]
        date_str = parts[1]
        direction = parts[2]
        event = parts[3]

        return self.get_swipe_event_id(
            int(participant),
            datetime.strptime(date_str, "%Y-%m-%d").date(),
            int(event),
            direction,
        )

    def get_swipe_event_summary_plot_data(self):
        """
        Build summary metrics for swipe events by scanning metadata.csv files.

        - Uses module-level `dataroot` so tests can point at a temp tree.
        - Falls back to DB-provided metrics when available and shaped as a list.
        """
        # Prefer DB metrics when real DB is attached and returns a list
        try:
            db_rows = self.db.get_local_metrics()
        except Exception:
            db_rows = None

        if isinstance(db_rows, list):
            out = {}
            for r in db_rows:
                avg = r["average_bounding_box_size"]
                out[r["event_id"]] = {
                    "event_id": r["event_id"],
                    "avg_box_size": float(avg) if avg is not None else None,
                    "footstep_count": int(r["step_count"])
                    if r["step_count"] is not None
                    else None,
                }
            return out

        # Fallback: scan filesystem
        base = Path(dataroot)
        out: dict = {}

        for meta_path in base.rglob("metadata.csv"):
            event_id = self.get_event_id_from_URI(meta_path)
            if not event_id:
                continue

            try:
                with meta_path.open(newline="") as f:
                    reader = csv.DictReader(f)
                    areas: list[float] = []
                    for row in reader:
                        x_min = int(row["XMin"])
                        x_max = int(row["XMax"])
                        y_min = int(row["YMin"])
                        y_max = int(row["YMax"])
                        areas.append((x_max - x_min) * (y_max - y_min))
            except Exception:
                continue  # skip malformed files

            if not areas:
                continue

            out[event_id] = {
                "event_id": event_id,
                "avg_box_size": sum(areas) / len(areas),
                "footstep_count": len(areas),
            }

        return out
