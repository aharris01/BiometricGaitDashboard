# backend/storage_access_layer/sal.py

# Standard library
import atexit
import os
import csv
from datetime import date, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse
from typing import Dict, List, Literal, Optional, Tuple, cast

# Third-party
import numpy as np

# Local
from . import validators as v
from .db.db import DB
from .db.schema import (
    LocalMetrics,
    LocalSwipeEvent,
    ManifestMetrics,
    ManifestSwipeEvent,
)
from sqlalchemy import and_, exists, extract, func, select

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

    # =========================================================
    # Footstep metadata access
    # =========================================================
    # These helpers read footstep information tied to one event.
    #
    # Important:
    # - get_footsteps() currently reads from metadata.csv on disk
    # - search_footsteps() uses the DB-backed footstep search path
    #
    # So this section is mainly for event-specific detail views,
    # while the footstep page search uses the DB layer.
    # =========================================================

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

        # Keep database access behind the DB layer. The DB implementation decides
        # whether the underlying footstep row comes from local.db or manifest.db.
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

        # vol is the full footstep pressure volume across time.
        # Shape: (time, height, width)
        vol = steps_npz[key]  # (T, H, W)

        # step_p100 is the max pressure image for this footstep.
        # This is used for footstep heatmap-style rendering.
        step_p100 = vol.max(axis=0)  # (H, W)

        # step_grf is the per-frame total pressure signal.
        # This is used like a simple force-over-time curve.
        step_grf = vol.reshape(vol.shape[0], -1).sum(axis=1)  # (T,)

        return step_p100, step_grf.tolist(), None

    # Return the max-pressure image for every footstep in one event.
    # This is mainly used by the summary view when many footsteps
    # need to be shown without loading each one separately.

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

    # Return both the max-pressure image and force-over-time data
    # for every footstep in one event.
    #
    # This is a heavier helper than get_all_footstep_p100() and is
    # meant for views that need both visual and time-series data.

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

    def _apply_local_availability_filter(self, query):
        return query.where(
            exists().where(
                and_(
                    LocalSwipeEvent.event_id == ManifestSwipeEvent.event_id,
                    LocalSwipeEvent.present.is_(True),
                )
            )
        )

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

        date_from = filters.get("date_from")
        date_to = filters.get("date_to")

        if date_from:
            query = query.where(ManifestSwipeEvent.date >= date_from)

        if date_to:
            query = query.where(ManifestSwipeEvent.date <= date_to)

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
            query = (
                select(
                    LocalMetrics.event_id,
                    getattr(LocalMetrics, x).label(x),
                    getattr(LocalMetrics, y).label(y),
                )
                .select_from(LocalMetrics)
                .join(
                    ManifestSwipeEvent,
                    ManifestSwipeEvent.event_id == LocalMetrics.event_id,
                )
            )

            query = self._apply_local_availability_filter(query)
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
            if hasattr(row, "_mapping"):
                row_dict = dict(row._mapping)
            else:
                row_dict = dict(row)

            event_id = row_dict.pop("event_id")
            output[event_id] = row_dict

        return output

    def get_date_bounds(self, filters: dict | None = None):
        with self.db._get_session() as session:
            query = (
                select(
                    func.min(ManifestSwipeEvent.date),
                    func.max(ManifestSwipeEvent.date),
                )
                .select_from(LocalMetrics)
                .join(
                    ManifestSwipeEvent,
                    ManifestSwipeEvent.event_id == LocalMetrics.event_id,
                )
            )

            query = self._apply_local_availability_filter(query)
            query = self._apply_summary_filters(query, filters)

            row = session.execute(query).first()

        if not row or row[0] is None or row[1] is None:
            return {"min_date": None, "max_date": None}

        return {
            "min_date": row[0].isoformat(),
            "max_date": row[1].isoformat(),
        }

    def get_distinct_date_values(self, part: str, filters: dict | None = None):
        if part not in {"year", "month", "day"}:
            raise ValueError("Invalid date part")

        with self.db._get_session() as session:
            query = (
                select(extract(part, ManifestSwipeEvent.date).label(part))
                .select_from(LocalMetrics)
                .join(
                    ManifestSwipeEvent,
                    ManifestSwipeEvent.event_id == LocalMetrics.event_id,
                )
                .distinct()
                .order_by(part)
            )

            query = self._apply_local_availability_filter(query)
            query = self._apply_summary_filters(query, filters)

            rows = session.execute(query).all()

        return sorted({int(r[0]) for r in rows if r[0] is not None})

    # =========================================================
    # Footstep page search
    # =========================================================
    # This is the main SAL entry point for the Footsteps view.
    #
    # Responsibilities:
    # - normalize incoming filter values
    # - pass filters to the DB layer
    # - reshape DB rows into a frontend-friendly response
    #
    # The DB layer owns the actual SQL filtering logic.
    # =========================================================

    def search_footsteps(
        self,
        event_ids: list[str] | None = None,
        participants: list[int] | None = None,
        date_from=None,
        date_to=None,
        width_min: int | None = None,
        width_max: int | None = None,
        height_min: int | None = None,
        height_max: int | None = None,
        size_min: int | None = None,
        size_max: int | None = None,
        offset: int = 0,
        limit: int = 60,
    ):
        normalized_ids = None
        if event_ids:
            normalized_ids = [str(event_id) for event_id in event_ids if event_id]

        normalized_participants = None
        if participants:
            normalized_participants = [int(p) for p in participants]

        rows, total = self.db.search_footsteps(
            event_ids=normalized_ids,
            participants=normalized_participants,
            date_from=date_from,
            date_to=date_to,
            width_min=width_min,
            width_max=width_max,
            height_min=height_min,
            height_max=height_max,
            size_min=size_min,
            size_max=size_max,
            offset=offset,
            limit=limit,
        )

        items = []
        for row in rows:
            items.append(
                {
                    "event_id": row["event_id"],
                    "footstep_id": row["footstep_id"],
                    "participant": row["participant"],
                    "date": row["date"].isoformat()
                    if row["date"] is not None
                    else None,
                    "start_frame": row["start_frame"],
                    "end_frame": row["end_frame"],
                    "x_min": row["x_min"],
                    "x_max": row["x_max"],
                    "y_min": row["y_min"],
                    "y_max": row["y_max"],
                    "bbox_width": row["bbox_width"],
                    "bbox_height": row["bbox_height"],
                    "bbox_area": row["bbox_area"],
                }
            )

        return {"items": items, "total": total}
