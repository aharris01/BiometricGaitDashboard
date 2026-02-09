# backend/storage_access_layer/sal.py

# Standard library
import atexit
import csv
import os
from datetime import date, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse
from typing import Dict, List, Literal, Optional, Tuple, cast

# Third-party
import numpy as np

# Local
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

    # =========================================================
    # Summary plot helpers
    # =========================================================
    def get_event_id_from_URI(self, file_path: str | Path) -> Optional[str]:
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

    # =========================================================
    # Local metrics accessors
    # =========================================================
    # Summary metrics are primarily read from the local database
    # (local_metrics). A generic column accessor is used to
    # retrieve individual metrics, while semantic helper
    # functions expose specific values.
    #
    # get_swipe_event_summary_plot_data() composes these accessors
    # and provides a stable, frontend-facing API. If database
    # access fails, metrics are recomputed from the filesystem
    # as a fallback.
    # =========================================================

    def get_local_metric(self, column_name: str):
        try:
            rows = self.db.get_local_metrics()
        except Exception:
            return None

        if not isinstance(rows, list):
            return None

        out = {}
        for r in rows:
            out[r["event_id"]] = r.get(column_name)

        return out

    # ---- Metric-specific accessors ----
    # Add one accessor per metric stored in local_metrics.
    # Each accessor should call get_local_metric() with the
    # corresponding column name.

    def get_average_bounding_box_sizes(self):
        return self.get_local_metric("average_bounding_box_size")

    def get_footstep_counts(self):
        return self.get_local_metric("step_count")

    # ---- Summary composition ----

    def get_swipe_event_summary_plot_data(self):
        summary_plot_data: dict = {}

        # =====================================================
        # Add new metric accessors here.
        #
        # For each new metric:
        #   1. Call the metric-specific accessor
        #   2. Merge its values into summary_plot_data below
        # =====================================================

        avg_boxes = self.get_average_bounding_box_sizes()
        steps = self.get_footstep_counts()

        # ---- Merge average bounding box size ----
        if avg_boxes is not None:
            for event_id, value in avg_boxes.items():
                summary_plot_data.setdefault(event_id, {})["avg_box_size"] = (
                    float(value) if value is not None else None
                )

        # ---- Merge footstep count ----
        if steps is not None:
            for event_id, value in steps.items():
                summary_plot_data.setdefault(event_id, {})["footstep_count"] = (
                    int(value) if value is not None else None
                )

        if summary_plot_data:
            for event_id, data in summary_plot_data.items():
                data["event_id"] = event_id
            return summary_plot_data

        # Fallback: filesystem scan
        return self._compute_metrics_from_filesystem()

    # ---- Filesystem fallback ----

    def _compute_metrics_from_filesystem(self):
        base = Path(dataroot)
        out = {}

        for meta_path in base.rglob("metadata.csv"):
            event_id = self.get_event_id_from_URI(meta_path)
            if not event_id:
                continue

            try:
                with meta_path.open(newline="") as f:
                    reader = csv.DictReader(f)
                    areas = []
                    for row in reader:
                        x_min = int(row["XMin"])
                        x_max = int(row["XMax"])
                        y_min = int(row["YMin"])
                        y_max = int(row["YMax"])
                        areas.append((x_max - x_min) * (y_max - y_min))
            except Exception:
                continue

            if not areas:
                continue

            # =================================================
            # When adding a new metric, update this dictionary
            # to include the filesystem-derived value for that
            # metric (if applicable).
            # =================================================
            out[event_id] = {
                "event_id": event_id,
                "avg_box_size": sum(areas) / len(areas),
                "footstep_count": len(areas),
            }

        return out
