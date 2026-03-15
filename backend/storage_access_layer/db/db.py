# backend/storage_access_layer/db.py

import os
from pathlib import Path
from dotenv import load_dotenv

from sqlalchemy import Engine, create_engine, event, exists, and_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from sqlalchemy import select, distinct, func

from backend.storage_access_layer.db.models import SwipeEvent
from .schema import (
    LocalBase,
    LocalSwipeEvent,
    LocalMetrics,
    LocalFootstep,
    LocalFootstepChange,
    ManifestMetrics,
    ManifestSwipeEvent,
    ManifestFootstep,
)
from ...scripts.ingest import iter_swipes


# -------------------------------------------------
# Environment / filesystem setup
# -------------------------------------------------

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = PROJECT_ROOT / "manifest.db"

# DATAROOT is still the dataset root used for local files and ingest.
DATAROOT = Path(os.environ.get("DATAROOT", "."))

# local.db should live in one consistent place regardless of dataset location.
LOCAL_DB_PATH = PROJECT_ROOT / "local.db"


# -------------------------------------------------
# Shared query helpers
# -------------------------------------------------


def apply_local_filter(query):
    # Restrict a manifest-based query to events that are available locally.
    # This keeps the UI focused on data that exists on disk for this machine.
    return query.where(
        exists().where(
            and_(
                LocalSwipeEvent.event_id == ManifestSwipeEvent.event_id,
                LocalSwipeEvent.present.is_(True),
            )
        )
    )


def event_base_path(event) -> Path:
    # Build the dataset path for one swipe event using manifest fields.
    # Example: <DATAROOT>/<participant>/<date>/<direction>/<event_number>
    return (
        DATAROOT
        / str(event.participant)
        / event.date.isoformat()
        / event.direction
        / str(event.event_number)
    )


# -------------------------------------------------
# Main DB access class
# -------------------------------------------------


class DB:
    def __init__(self, engine: Engine | None = None):
        # Engine can be provided for testing
        self._owns_engine = engine is None

        if self._owns_engine:
            # In normal app use, create the local DB engine here.
            self.engine, created_new = _init_db()
        else:  # Engine has been provided for testing
            assert engine is not None
            self.engine = engine
            created_new = False

        # SessionLocal is the single session factory used by this class.
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        # add_local_availability_filter(self.SessionLocal)

        # If this is a brand-new local DB, seed it from the local dataset
        # and the read-only manifest database.
        if self._owns_engine and created_new:
            _seed_db(self)

    @contextmanager
    def _get_session(self):
        # Open a session, commit on success, and roll back on failure.
        # This keeps transaction handling consistent across the file.
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self):
        # Dispose the engine when the DB object is no longer needed.
        if self.engine:
            self.engine.dispose()

    # -------------------------------------------------
    # Local event registration
    # -------------------------------------------------

    # New add_swipe_event function that accepts a LocalSwipeEvent object
    def add_swipe_event(self, swipe_event_obj: LocalSwipeEvent):
        # Add one locally available swipe event to local.db.
        # This is used during local DB seeding.
        with self._get_session() as session:
            try:
                session.add(swipe_event_obj)
            except Exception as e:
                print(f"{e}: Duplicate found")

    # -------------------------------------------------
    # Swipe-event metadata queries
    # -------------------------------------------------

    # identical logic to previous version of accessfunctions.py
    def get_participants(self):
        # Return the list of participants that have locally available events.
        query = apply_local_filter(
            select(distinct(ManifestSwipeEvent.participant))
        ).order_by(ManifestSwipeEvent.participant)

        with self._get_session() as session:
            return session.scalars(query).all()

    def get_dates(self, participant):
        # Return available dates for one participant.
        query = apply_local_filter(
            select(distinct(ManifestSwipeEvent.date)).where(
                ManifestSwipeEvent.participant == participant
            )
        ).order_by(ManifestSwipeEvent.date)

        with self._get_session() as session:
            return session.scalars(query).all()

    def get_directions(self, participant, date):
        # Return available directions for one participant and date.
        query = apply_local_filter(
            select(distinct(ManifestSwipeEvent.direction)).where(
                ManifestSwipeEvent.participant == participant,
                ManifestSwipeEvent.date == date,
            )
        ).order_by(ManifestSwipeEvent.direction)

        with self._get_session() as session:
            return session.scalars(query).all()

    def get_events(self, participant, date, direction):
        # Return event numbers for one participant/date/direction combination.
        query = apply_local_filter(
            select(distinct(ManifestSwipeEvent.event_number)).where(
                ManifestSwipeEvent.participant == participant,
                ManifestSwipeEvent.date == date,
                ManifestSwipeEvent.direction == direction,
            )
        ).order_by(ManifestSwipeEvent.event_number)

        with self._get_session() as session:
            return session.scalars(query).all()

    def get_swipe_event_id(self, participant, date, event, direction):
        # Resolve the event_id for one participant/date/event/direction selection.
        query = apply_local_filter(
            select(ManifestSwipeEvent.event_id).where(
                ManifestSwipeEvent.participant == participant,
                ManifestSwipeEvent.date == date,
                ManifestSwipeEvent.event_number == event,
                ManifestSwipeEvent.direction == direction,
            )
        )

        with self._get_session() as session:
            return session.scalars(query).first()

    def get_swipe_event(self, event_id):
        # Build the full SwipeEvent model used by the rest of the app.
        # This combines manifest metadata with the local root path.
        query = (
            select(ManifestSwipeEvent, LocalSwipeEvent.root_path)
            .join(
                LocalSwipeEvent, LocalSwipeEvent.event_id == ManifestSwipeEvent.event_id
            )
            .where(ManifestSwipeEvent.event_id == event_id)
        )
        with self._get_session() as session:
            row = session.execute(query).first()
            if row is None:
                return None
            event, root_path = row

            event_dict = {
                "event_id": event.event_id,
                "participant": event.participant,
                "date": event.date.isoformat(),
                "direction": event.direction,
                "event_number": event.event_number,
                "trial_npz_uri": f"{root_path}/trial.npz",
                "trial_p100_npz_uri": f"{root_path}/trial.p100.npz",
                "trial_grf_npz_uri": f"{root_path}/trial.grf.npz",
            }

            return SwipeEvent(**event_dict)

    def get_local_event_ids(self):
        # Return all event IDs tracked in local.db.
        query = select(LocalSwipeEvent.event_id)

        with self._get_session() as session:
            return session.scalars(query).all()

    def get_local_metrics(self):
        # Return the local metrics rows joined with participant metadata.
        # This is used by the metrics view in the frontend.
        query = (
            select(
                LocalMetrics.event_id,
                LocalMetrics.avg_bbox_size,
                LocalMetrics.step_count,
                ManifestSwipeEvent.participant,
            )
            .join(
                ManifestSwipeEvent,
                ManifestSwipeEvent.event_id == LocalMetrics.event_id,
            )
            .group_by(
                LocalMetrics.event_id,
                ManifestSwipeEvent.participant,
            )
        )

        with self._get_session() as session:
            return session.execute(query).mappings().all()

    # -------------------------------------------------
    # Footstep view DB queries
    # -------------------------------------------------

    def get_event_footsteps(self, event_id: str):
        # Return all footsteps for one event from local.db.
        # This supports event-specific footstep inspection.
        query = (
            select(
                LocalFootstep.footstep_id,
                LocalFootstep.start_frame,
                LocalFootstep.end_frame,
                LocalFootstep.x_min,
                LocalFootstep.x_max,
                LocalFootstep.y_min,
                LocalFootstep.y_max,
            )
            .where(LocalFootstep.event_id == event_id)
            .order_by(LocalFootstep.footstep_id)
        )

        with self._get_session() as session:
            return session.execute(query).mappings().all()

    def get_single_footstep(self, event_id: str, footstep_id: int):
        # Return one footstep row from local.db.
        # This is the smallest lookup used by the SAL and image routes.
        query = select(LocalFootstep).where(
            LocalFootstep.event_id == event_id,
            LocalFootstep.footstep_id == footstep_id,
        )

        with self._get_session() as session:
            return session.scalars(query).first()

    def get_local_footstep_changes(self, event_id: str, footstep_id: int):
        # Return all local changelog rows for one footstep.
        query = (
            select(LocalFootstepChange)
            .where(
                LocalFootstepChange.event_id == event_id,
                LocalFootstepChange.footstep_id == footstep_id,
            )
            .order_by(
                LocalFootstepChange.changed_at.desc(),
                LocalFootstepChange.id.desc(),
            )
        )

        with self._get_session() as session:
            return session.scalars(query).all()

    def get_next_local_footstep_id(self, event_id: str):
        # Return the next available local footstep ID for one event.
        query = select(func.max(LocalFootstep.footstep_id)).where(
            LocalFootstep.event_id == event_id
        )

        with self._get_session() as session:
            current_max = session.execute(query).scalar_one_or_none()

        if current_max is None:
            return 0

        return int(current_max) + 1

    def create_local_footstep(
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
        # Create one new local footstep row and log the create action.
        with self._get_session() as session:
            next_footstep_id = self.get_next_local_footstep_id(event_id)

            row = LocalFootstep(
                event_id=event_id,
                footstep_id=next_footstep_id,
                start_frame=int(start_frame),
                end_frame=int(end_frame),
                x_min=int(x_min),
                x_max=int(x_max),
                y_min=int(y_min),
                y_max=int(y_max),
                label=label,
            )

            session.add(row)

            session.add(
                LocalFootstepChange(
                    event_id=event_id,
                    footstep_id=next_footstep_id,
                    action="create",
                    old_x_min=None,
                    old_x_max=None,
                    old_y_min=None,
                    old_y_max=None,
                    old_label=None,
                    new_x_min=int(x_min),
                    new_x_max=int(x_max),
                    new_y_min=int(y_min),
                    new_y_max=int(y_max),
                    new_label=label,
                )
            )

            session.flush()
            session.refresh(row)
            return row

    def delete_local_footstep(self, event_id: str, footstep_id: int):
        # Delete one local footstep row and log the delete action.
        query = select(LocalFootstep).where(
            LocalFootstep.event_id == event_id,
            LocalFootstep.footstep_id == footstep_id,
        )

        with self._get_session() as session:
            row = session.scalars(query).first()
            if row is None:
                return None

            session.add(
                LocalFootstepChange(
                    event_id=event_id,
                    footstep_id=footstep_id,
                    action="delete",
                    old_x_min=int(row.x_min),
                    old_x_max=int(row.x_max),
                    old_y_min=int(row.y_min),
                    old_y_max=int(row.y_max),
                    old_label=row.label,
                    new_x_min=None,
                    new_x_max=None,
                    new_y_min=None,
                    new_y_max=None,
                    new_label=None,
                )
            )

            session.delete(row)
            return True

    def update_local_footstep(
        self,
        event_id: str,
        footstep_id: int,
        *,
        x_min: int,
        x_max: int,
        y_min: int,
        y_max: int,
        start_frame: int,
        end_frame: int,
        label: str | None,
    ):
        # Update one local footstep row in local.db.
        #
        # Before the row is updated, write the old/new values to the local
        # changelog table so manual edits remain traceable.
        query = select(LocalFootstep).where(
            LocalFootstep.event_id == event_id,
            LocalFootstep.footstep_id == footstep_id,
        )

        with self._get_session() as session:
            row = session.scalars(query).first()
            if row is None:
                return None

            old_x_min = int(row.x_min)
            old_x_max = int(row.x_max)
            old_y_min = int(row.y_min)
            old_y_max = int(row.y_max)
            old_start_frame = int(row.start_frame)
            old_end_frame = int(row.end_frame)
            old_label = row.label

            new_x_min = int(x_min)
            new_x_max = int(x_max)
            new_y_min = int(y_min)
            new_y_max = int(y_max)
            new_start_frame = int(start_frame)
            new_end_frame = int(end_frame)
            new_label = label

            # Do not create a changelog row if nothing actually changed.
            if (
                old_x_min == new_x_min
                and old_x_max == new_x_max
                and old_y_min == new_y_min
                and old_y_max == new_y_max
                and old_start_frame == new_start_frame
                and old_end_frame == new_end_frame
                and old_label == new_label
            ):
                return row

            session.add(
                LocalFootstepChange(
                    event_id=event_id,
                    footstep_id=footstep_id,
                    action="edit",
                    old_x_min=old_x_min,
                    old_x_max=old_x_max,
                    old_y_min=old_y_min,
                    old_y_max=old_y_max,
                    old_start_frame=old_start_frame,
                    old_end_frame=old_end_frame,
                    old_label=old_label,
                    new_x_min=new_x_min,
                    new_x_max=new_x_max,
                    new_y_min=new_y_min,
                    new_y_max=new_y_max,
                    new_start_frame=new_start_frame,
                    new_end_frame=new_end_frame,
                    new_label=new_label,
                )
            )

            row.x_min = new_x_min
            row.x_max = new_x_max
            row.y_min = new_y_min
            row.y_max = new_y_max
            row.start_frame = new_start_frame
            row.end_frame = new_end_frame
            row.label = new_label

            session.flush()
            session.refresh(row)
            return row

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
        # Footstep search uses the local mirror table for editable/local rows,
        # and joins manifest swipe-event metadata only for participant/date filters.
        bbox_width = LocalFootstep.x_max - LocalFootstep.x_min
        bbox_height = LocalFootstep.y_max - LocalFootstep.y_min
        bbox_area = bbox_width * bbox_height

        # Limit search results to events that are currently present locally.
        local_event_ids = select(LocalSwipeEvent.event_id).where(
            LocalSwipeEvent.present.is_(True)
        )

        # Main query used to fetch the visible result rows.
        items_query = (
            select(
                LocalFootstep.event_id,
                LocalFootstep.footstep_id,
                ManifestSwipeEvent.participant,
                ManifestSwipeEvent.date,
                LocalFootstep.start_frame,
                LocalFootstep.end_frame,
                LocalFootstep.x_min,
                LocalFootstep.x_max,
                LocalFootstep.y_min,
                LocalFootstep.y_max,
                bbox_width.label("bbox_width"),
                bbox_height.label("bbox_height"),
                bbox_area.label("bbox_area"),
                (ManifestFootstep.footstep_id.is_not(None)).label("has_thumbnail"),
            )
            .select_from(LocalFootstep)
            .join(
                ManifestSwipeEvent,
                ManifestSwipeEvent.event_id == LocalFootstep.event_id,
            )
            .outerjoin(
                ManifestFootstep,
                and_(
                    ManifestFootstep.event_id == LocalFootstep.event_id,
                    ManifestFootstep.footstep_id == LocalFootstep.footstep_id,
                ),
            )
            .where(LocalFootstep.event_id.in_(local_event_ids))
        )

        # Separate count query used for pagination.
        count_query = (
            select(func.count())
            .select_from(LocalFootstep)
            .join(
                ManifestSwipeEvent,
                ManifestSwipeEvent.event_id == LocalFootstep.event_id,
            )
            .where(LocalFootstep.event_id.in_(local_event_ids))
        )

        # Apply filters only when the caller provides them.
        if event_ids:
            items_query = items_query.where(LocalFootstep.event_id.in_(event_ids))
            count_query = count_query.where(LocalFootstep.event_id.in_(event_ids))

        if participants:
            items_query = items_query.where(
                ManifestSwipeEvent.participant.in_(participants)
            )
            count_query = count_query.where(
                ManifestSwipeEvent.participant.in_(participants)
            )

        if date_from is not None:
            items_query = items_query.where(ManifestSwipeEvent.date >= date_from)
            count_query = count_query.where(ManifestSwipeEvent.date >= date_from)

        if date_to is not None:
            items_query = items_query.where(ManifestSwipeEvent.date <= date_to)
            count_query = count_query.where(ManifestSwipeEvent.date <= date_to)

        if width_min is not None:
            items_query = items_query.where(bbox_width >= int(width_min))
            count_query = count_query.where(bbox_width >= int(width_min))

        if width_max is not None:
            items_query = items_query.where(bbox_width <= int(width_max))
            count_query = count_query.where(bbox_width <= int(width_max))

        if height_min is not None:
            items_query = items_query.where(bbox_height >= int(height_min))
            count_query = count_query.where(bbox_height >= int(height_min))

        if height_max is not None:
            items_query = items_query.where(bbox_height <= int(height_max))
            count_query = count_query.where(bbox_height <= int(height_max))

        if size_min is not None:
            items_query = items_query.where(bbox_area >= int(size_min))
            count_query = count_query.where(bbox_area >= int(size_min))

        if size_max is not None:
            items_query = items_query.where(bbox_area <= int(size_max))
            count_query = count_query.where(bbox_area <= int(size_max))

        # Apply stable ordering before pagination.
        items_query = (
            items_query.order_by(
                LocalFootstep.event_id,
                LocalFootstep.footstep_id,
            )
            .offset(offset)
            .limit(limit)
        )

        with self._get_session() as session:
            total = int(session.execute(count_query).scalar_one() or 0)
            rows = session.execute(items_query).mappings().all()

        return rows, total


# -------------------------------------------------
# DB initialisation helpers
# -------------------------------------------------


def _init_db():
    # Local database is writable and always lives at the project root.
    local_uri = f"sqlite:///{LOCAL_DB_PATH.as_posix()}"

    # Manifest database is read-only mode
    manifest_uri = f"file:{MANIFEST_PATH.as_posix()}?mode=ro"

    engine = create_engine(
        local_uri, connect_args={"check_same_thread": False, "uri": True}
    )

    @event.listens_for(engine, "connect")
    def _attach_manifest(dbapi_conn, _):
        # Attach the read-only manifest DB every time a new SQLite connection opens.
        cur = dbapi_conn.cursor()
        cur.execute(
            "ATTACH DATABASE ? AS manifest;",
            (manifest_uri,),
        )
        cur.close()

    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table';")
        ).fetchall()

    created_new = not rows

    # Always create any missing local tables.
    LocalBase.metadata.create_all(engine)

    return engine, created_new


def _seed_db(db: DB):
    # Scan the local dataset and register the swipe events that exist on disk.
    for swipe_data in iter_swipes(DATAROOT):
        swipe_event_obj = LocalSwipeEvent(**swipe_data)
        with db._get_session() as session:
            query = select(ManifestSwipeEvent).where(
                ManifestSwipeEvent.event_id == swipe_event_obj.event_id
            )
            result = session.execute(query).first()
            if result is None:
                continue  # Skip if event_id not found in manifest
        db.add_swipe_event(swipe_event_obj)

    # After local swipe events are seeded, mirror the supporting local tables
    # from the read-only manifest database.
    copy_metrics_from_manifest_to_local(db)
    copy_footsteps_from_manifest_to_local(db)


def copy_metrics_from_manifest_to_local(db: DB):
    # Copy metrics for locally present events from manifest.global_metrics
    # into local_metrics. Existing rows are updated in place.
    #
    # Returns the number of rows SQLite reports as affected.

    with db._get_session() as session:
        local_event_ids = select(LocalSwipeEvent.event_id).where(
            LocalSwipeEvent.present.is_(True)
        )

        select_stmt = select(
            ManifestMetrics.event_id,
            ManifestMetrics.avg_bbox_size,
            ManifestMetrics.std_dev_bounding_box_area,
            ManifestMetrics.variance_bounding_box_area,
            ManifestMetrics.mean_width,
            ManifestMetrics.mean_height,
            ManifestMetrics.variance_bounding_box_width,
            ManifestMetrics.variance_bounding_box_height,
            ManifestMetrics.step_count,
            ManifestMetrics.step_count_on_path,
            ManifestMetrics.total_trial_area,
            ManifestMetrics.mean_step_distance,
            ManifestMetrics.variance_step_distance,
            ManifestMetrics.active_trial_duration_all,
            ManifestMetrics.active_trial_duration_path,
            ManifestMetrics.max_footstep_duration_frames,
            ManifestMetrics.mean_heading_angle,
            ManifestMetrics.std_heading_angle,
            ManifestMetrics.variance_heading_angle,
        ).where(ManifestMetrics.event_id.in_(local_event_ids))

        insert_stmt = sqlite_insert(LocalMetrics).from_select(
            [
                LocalMetrics.event_id,
                LocalMetrics.avg_bbox_size,
                LocalMetrics.std_dev_bounding_box_area,
                LocalMetrics.variance_bounding_box_area,
                LocalMetrics.mean_width,
                LocalMetrics.mean_height,
                LocalMetrics.variance_bounding_box_width,
                LocalMetrics.variance_bounding_box_height,
                LocalMetrics.step_count,
                LocalMetrics.step_count_on_path,
                LocalMetrics.total_trial_area,
                LocalMetrics.mean_step_distance,
                LocalMetrics.variance_step_distance,
                LocalMetrics.active_trial_duration_all,
                LocalMetrics.active_trial_duration_path,
                LocalMetrics.max_footstep_duration_frames,
                LocalMetrics.mean_heading_angle,
                LocalMetrics.std_heading_angle,
                LocalMetrics.variance_heading_angle,
            ],
            select_stmt,
        )

        stmt = insert_stmt.on_conflict_do_update(
            index_elements=[LocalMetrics.event_id],
            set_={
                "avg_bbox_size": insert_stmt.excluded.avg_bbox_size,
                "std_dev_bounding_box_area": insert_stmt.excluded.std_dev_bounding_box_area,
                "variance_bounding_box_area": insert_stmt.excluded.variance_bounding_box_area,
                "mean_width": insert_stmt.excluded.mean_width,
                "mean_height": insert_stmt.excluded.mean_height,
                "variance_bounding_box_width": insert_stmt.excluded.variance_bounding_box_width,
                "variance_bounding_box_height": insert_stmt.excluded.variance_bounding_box_height,
                "step_count": insert_stmt.excluded.step_count,
                "step_count_on_path": insert_stmt.excluded.step_count_on_path,
                "total_trial_area": insert_stmt.excluded.total_trial_area,
                "mean_step_distance": insert_stmt.excluded.mean_step_distance,
                "variance_step_distance": insert_stmt.excluded.variance_step_distance,
                "active_trial_duration_all": insert_stmt.excluded.active_trial_duration_all,
                "active_trial_duration_path": insert_stmt.excluded.active_trial_duration_path,
                "max_footstep_duration_frames": insert_stmt.excluded.max_footstep_duration_frames,
                "mean_heading_angle": insert_stmt.excluded.mean_heading_angle,
                "std_heading_angle": insert_stmt.excluded.std_heading_angle,
                "variance_heading_angle": insert_stmt.excluded.variance_heading_angle,
            },
        )

        result = session.execute(stmt.returning(LocalMetrics.event_id))
        return int(len(result.scalars().all())) or 0


def copy_footsteps_from_manifest_to_local(db: DB) -> int:
    # Copy footstep rows for locally present events from manifest.footsteps
    # into local_footsteps. Existing rows are updated in place.
    #
    # The label field is not overwritten because it belongs to local review state.

    with db._get_session() as session:
        # event_ids that exist locally and are marked present
        local_event_ids = select(LocalSwipeEvent.event_id).where(
            LocalSwipeEvent.present.is_(True)
        )

        # rows to copy from manifest.footsteps
        src = select(
            ManifestFootstep.event_id,
            ManifestFootstep.footstep_id,
            ManifestFootstep.start_frame,
            ManifestFootstep.end_frame,
            ManifestFootstep.x_min,
            ManifestFootstep.x_max,
            ManifestFootstep.y_min,
            ManifestFootstep.y_max,
        ).where(ManifestFootstep.event_id.in_(local_event_ids))

        # INSERT ... SELECT ... with ON CONFLICT(event_id, footstep_id) DO UPDATE
        insert_stmt = sqlite_insert(LocalFootstep).from_select(
            [
                "event_id",
                "footstep_id",
                "start_frame",
                "end_frame",
                "x_min",
                "x_max",
                "y_min",
                "y_max",
            ],
            src,
        )

        stmt = insert_stmt.on_conflict_do_update(
            index_elements=[LocalFootstep.event_id, LocalFootstep.footstep_id],
            set_={
                "start_frame": insert_stmt.excluded.start_frame,
                "end_frame": insert_stmt.excluded.end_frame,
                "x_min": insert_stmt.excluded.x_min,
                "x_max": insert_stmt.excluded.x_max,
                "y_min": insert_stmt.excluded.y_min,
                "y_max": insert_stmt.excluded.y_max,
                # Intentionally do not overwrite label here because label is
                # local-only review state that should remain owned by local.db.
            },
        )

        result = session.execute(stmt.returning(LocalFootstep.event_id))
        return int(len(result.scalars().all())) or 0
