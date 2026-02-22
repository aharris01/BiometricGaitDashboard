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
from .db.schema import ManifestMetrics, ManifestSwipeEvent, ManifestFootstep
from sqlalchemy import select, extract

DATAROOT = Path(
    os.environ.get("DATAROOT", os.environ.get("dataroot", "."))
)  # Defaults to root
# Lowercase alias so tests can monkeypatch `sal_mod.dataroot`
dataroot = DATAROOT


def uri_to_path(uri: str) -> Path:
    """
    Accept:
      - file:// URIs
      - plain filesystem paths

    Reject:
      - any other URI scheme (http://, s3://, etc.)
    """
    s = str(uri)

    if "://" in s and not s.startswith("file://"):
        raise ValueError(f"Unsupported URI scheme in {uri!r}; expected file://")

    if not s.startswith("file://"):
        return Path(s)

    parsed = urlparse(s)
    path = unquote(parsed.path)

    # Windows: "/C:/Users/..." -> "C:/Users/..."
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

    # -------------------------------------------------
    # Footstep view DB for single footstep. To be added
    # to "get_footsteps()" for refactor allowing for faster
    # summary view footstep performance
    # -------------------------------------------------
    def get_single_footstep(self, event_id: str, footstep_id: int):
        event = self.db.get_swipe_event(event_id)
        if event is None:
            return None, "missing_event"

        row = self.db.get_single_footstep(event_id, footstep_id)

        if row is None:
            return None, "missing_file"

        return (
            {
                "id": row.footstep_id,
                "start_frame": row.start_frame,
                "end_frame": row.end_frame,
                "x_min": row.x_min,
                "x_max": row.x_max,
                "y_min": row.y_min,
                "y_max": row.y_max,
            },
            None,
        )

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
        # Normalize Windows separators so this works on macOS/Linux too (and in unit tests)
        normalized = str(file_path).replace("\\", "/")
        p = Path(normalized)

        # Make relative to dataroot if possible
        try:
            rel = p.relative_to(Path(dataroot))
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

    def get_participants_by_event(self):
        return self.get_local_metric("participant")

    # ---- Summary composition ----

    def get_available_metrics(self) -> list[str]:
        columns = ManifestMetrics.__table__.columns.keys()
        # just getting the metric names from the manfestmetrics table, not necessary to get event_id
        return [col for col in columns if col != "event_id"]

    # filter specifically for participant query
    def _apply_participant_filter(self, query, filters: dict | None):
        if not filters:
            return query

        if "participants" in filters:
            participants = filters["participants"]

            if participants:
                query = query.where(ManifestSwipeEvent.participant.in_(participants))

        return query

    # filter specifically for date query
    def _apply_date_filter(self, query, filters: dict | None):
        if not filters:
            return query

        if "year" in filters:
            year = filters["year"]
            if year:
                query = query.where(
                    extract("year", ManifestSwipeEvent.date) == int(year)
                )

        if "month" in filters:
            month = filters["month"]
            if month:
                query = query.where(
                    extract("month", ManifestSwipeEvent.date) == int(month)
                )

        if "day" in filters:
            day = filters["day"]
            if day:
                query = query.where(extract("day", ManifestSwipeEvent.date) == int(day))

        return query

    # full filter applier function. when adding new filters, update this helper.
    def _apply_summary_filters(self, query, filters: dict | None):
        if not filters:
            return query

        query = self._apply_participant_filter(query, filters)
        query = self._apply_date_filter(query, filters)

        return query

    def get_swipe_event_summary_plot_data(
        self, x: str, y: str, filters: dict | None = None
    ):
        # ------------------------------------------------------------------
        # Validate requested metrics
        #
        # The frontend must provide two metric names (x and y).
        # We verify that both exist in the ManifestMetrics table
        # to prevent invalid or arbitrary column access.
        # ------------------------------------------------------------------
        available = self.get_available_metrics()

        if x not in available:
            raise ValueError(f"Invalid metric requested for x-axis: {x}")

        if y not in available:
            raise ValueError(f"Invalid metric requested for y-axis: {y}")

        # ------------------------------------------------------------------
        # Build dynamic SELECT query
        #
        # Only select event_id and the requested metric columns.
        # This ensures the response payload contains exactly the
        # metrics needed for scatter plotting.
        # ------------------------------------------------------------------
        with self.db._get_session() as session:
            query = select(
                ManifestMetrics.event_id,
                getattr(ManifestMetrics, x),
                getattr(ManifestMetrics, y),
            ).join(
                ManifestSwipeEvent,
                ManifestSwipeEvent.event_id == ManifestMetrics.event_id,
            )

            query = self._apply_summary_filters(query, filters)

            results = session.execute(query).all()

        # ------------------------------------------------------------------
        # Format results
        #
        # Convert each SQLAlchemy row into a dictionary keyed by event_id.
        # The inner dictionary contains only the requested metrics.
        # ------------------------------------------------------------------
        output = {}

        for row in results:
            # Support for unit tests
            if hasattr(row, "_mapping"):
                row_dict = dict(row._mapping)
            else:
                row_dict = dict(row)

            event_id = row_dict.pop("event_id")
            output[event_id] = row_dict

        return output

    def get_distinct_date_part(
        self,
        part: str,
        filters: dict | None = None,
    ) -> list[int]:
        if part not in {"year", "month", "day"}:
            raise ValueError("Invalid date part")

        with self.db._get_session() as session:
            query = select(ManifestMetrics.event_id).join(
                ManifestSwipeEvent,
                ManifestSwipeEvent.event_id == ManifestMetrics.event_id,
            )

            query = self._apply_summary_filters(query, filters)

            stmt = (
                query.with_only_columns(
                    extract(part, ManifestSwipeEvent.date).label(part)
                )
                .distinct()
                .order_by(part)
            )

            rows = session.execute(stmt).all()

        return sorted({int(row[0]) for row in rows if row[0] is not None})

    # Legacy fallback — not used in runtime summary

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
