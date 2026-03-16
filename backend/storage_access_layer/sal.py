# backend/storage_access_layer/sal.py

# Standard library
import atexit
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from backend.storage_access_layer.helpers.common import CommonHelper

# Local
from .container import get_db
from .db.db import DB

from .helpers.sal_meta import SalMeta
from .helpers.sal_events import SalEvents
from .helpers.sal_metrics import SalMetrics
from .helpers.sal_footsteps import SalFootsteps
from .utils.types import FootstepSearchFilters

DATAROOT = Path(
    os.environ.get("DATAROOT", os.environ.get("dataroot", "."))
)  # Defaults to root
# Lowercase alias so tests can monkeypatch `sal_mod.dataroot`
dataroot = DATAROOT


class SAL:
    # =========================================================
    # Backend ↔ SAL to get data by event_id primary key
    # =========================================================

    def __init__(self, db: DB | None = None):
        self.db = db or get_db()
        self.common = CommonHelper(self.db)

        # Domain helpers. Meta methods are delegated through this helper now.
        self.meta = SalMeta(self.db, self.common)
        self.events = SalEvents(self.db, self.common)
        self.metrics = SalMetrics(self.db, self.common)
        self.footsteps = SalFootsteps(self.db, self.common)

        atexit.register(self._close_db)

    def _close_db(self) -> None:
        if getattr(self, "db", None):
            close = getattr(self.db, "close", None)
            if close:
                close()

    # =========================================================
    # Meta lookups (facade -> helper)
    # =========================================================

    def get_participants(self):
        return self.meta.get_participants()

    def get_dates(self, participant: int):
        return self.meta.get_dates(participant)

    def get_directions(self, participant: int, dt: date):
        return self.meta.get_directions(participant, dt)

    def get_events(self, participant: int, dt: date, direction: str):
        return self.meta.get_events(participant, dt, direction)

    def get_swipe_event_id(
        self, participant: int, dt: date, event: int, direction: str
    ):
        return self.meta.get_swipe_event_id(participant, dt, event, direction)

    def get_both_direction_events(self, participant: int, dt: date):
        return self.meta.get_both_direction_events(participant, dt)

    def get_event_summary(self, event_id: str):
        return self.events.get_event_summary(event_id)

    def get_p100(self, event_id: str):
        return self.events.get_p100(event_id)

    def get_footsteps(self, event_id: str):
        return self.footsteps.get_footsteps(event_id)

    def get_single_footstep(self, event_id: str, footstep_id: int):
        return self.footsteps.get_single_footstep(event_id, footstep_id)

    def get_footstep_review_context(self, event_id: str, footstep_id: int):
        return self.footsteps.get_footstep_review_context(event_id, footstep_id)

    def save_footstep_review(self, event_id: str, footstep_id: int, edits):
        return self.footsteps.save_footstep_review(event_id, footstep_id, edits)

    def create_footstep(
        self,
        event_id: str,
        *,
        start_frame: int,
        end_frame: int,
        x_min: int,
        x_max: int,
        y_min: int,
        y_max: int,
        label: str | None,
    ):
        return self.footsteps.create_footstep(
            event_id,
            start_frame=start_frame,
            end_frame=end_frame,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
            label=label,
        )

    def delete_footstep(self, event_id: str, footstep_id: int):
        return self.footsteps.delete_footstep(event_id, footstep_id)

    def get_footstep_data(self, event_id: str, step_id: int):
        return self.footsteps.get_footstep_data(event_id, step_id)

    def get_all_footstep_p100(self, event_id: str):
        return self.footsteps.get_all_footstep_p100(event_id)

    def get_all_footstep_details(self, event_id: str):
        return self.footsteps.get_all_footstep_details(event_id)

    # Read the frame count from the full trial volume for one event.
    #
    # Create mode needs this so new start_frame and end_frame values can be
    # checked against the real trial length before a local footstep is created.
    # This does not load any per-step data or recreate extraction outputs.
    def _get_trial_frame_count(self, event_id: str):
        event, err = self.common._require_event(event_id)
        if err or event is None:
            return None, err
        return self.common._get_trial_frame_count(event)

    def get_grf(self, event_id: str):
        return self.events.get_grf(event_id)

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
    # Summary metrics are read from the local database
    # (local_metrics). A generic column accessor is used to
    # retrieve individual metrics, while semantic helper
    # functions expose specific values.
    #
    # get_swipe_event_summary_plot_data() composes these accessors
    # and provides a stable, frontend-facing API. If database
    # access fails, metrics are recomputed from the filesystem
    # as a fallback.
    # =========================================================

    def get_available_metrics(self) -> list[str]:
        return self.metrics.get_available_metrics()

    def get_swipe_event_summary_plot_data(
        self, x: str, y: str, filters: dict | None = None
    ):
        return self.metrics.get_swipe_event_summary_plot_data(x, y, filters)

    def get_date_bounds(self, filters: dict | None = None):
        return self.metrics.get_date_bounds(filters)

    def get_distinct_date_values(self, part: str, filters: dict | None = None):
        return self.metrics.get_distinct_date_values(part, filters)

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

    def search_footsteps(self, filters: FootstepSearchFilters):
        return self.footsteps.search_footsteps(filters)
