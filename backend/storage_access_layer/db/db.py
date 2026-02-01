# backend/storage_access_layer/db.py
import os
from pathlib import Path
from dotenv import load_dotenv

from sqlalchemy import Engine, create_engine, event, exists, and_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from sqlalchemy import select, distinct

from backend.storage_access_layer.db.models import SwipeEvent
from .schema import (
    LocalBase,
    LocalSwipeEvent,
    LocalMetrics,
    ManifestMetrics,
    ManifestSwipeEvent,
)

from ...scripts.ingest import iter_swipes

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = PROJECT_ROOT / "manifest.db"

DATAROOT = Path(os.environ.get("DATAROOT", "."))  # Defaults to root


def apply_local_filter(query):
    return query.where(
        exists().where(
            and_(
                LocalSwipeEvent.event_id == ManifestSwipeEvent.event_id,
                LocalSwipeEvent.present.is_(True),
            )
        )
    )


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


class DB:
    def __init__(self, engine: Engine | None = None):
        # Engine can be provided for testing
        self._owns_engine = engine is None

        if self._owns_engine:
            self.engine, created_new = _init_db()
        else:  # Engine has been provided for testing
            assert engine is not None
            self.engine = engine
            created_new = False

        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        # add_local_availability_filter(self.SessionLocal)

        # Database needs to be populated with local data if it was just created
        if self._owns_engine and created_new:
            _seed_db(self)

    @contextmanager
    def _get_session(self):
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
        if self.engine:
            self.engine.dispose()

    # New add_swipe_event function that accepts a LocalSwipeEvent object
    def add_swipe_event(self, swipe_event_obj: LocalSwipeEvent):
        with self._get_session() as session:
            try:
                session.add(swipe_event_obj)
            except Exception as e:
                print(f"{e}: Duplicate found")

    # identical logic to previous version of accessfunctions.py
    def get_participants(self):
        query = apply_local_filter(
            select(distinct(ManifestSwipeEvent.participant))
        ).order_by(ManifestSwipeEvent.participant)

        with self._get_session() as session:
            return session.scalars(query).all()

    def get_dates(self, participant):
        query = apply_local_filter(
            select(distinct(ManifestSwipeEvent.date)).where(
                ManifestSwipeEvent.participant == participant
            )
        ).order_by(ManifestSwipeEvent.date)

        with self._get_session() as session:
            return session.scalars(query).all()

    def get_directions(self, participant, date):
        query = apply_local_filter(
            select(distinct(ManifestSwipeEvent.direction)).where(
                ManifestSwipeEvent.participant == participant,
                ManifestSwipeEvent.date == date,
            )
        ).order_by(ManifestSwipeEvent.direction)

        with self._get_session() as session:
            return session.scalars(query).all()

    def get_events(self, participant, date, direction):
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
        query = select(LocalSwipeEvent.event_id).where(
            LocalSwipeEvent.present.is_(True)
        )

        with self._get_session() as session:
            return session.scalars(query).all()


# -------------------------------------------------
# DB initialisation helpers
# -------------------------------------------------


def _init_db():
    # Local database is writable
    local_uri = f"sqlite:///{DATAROOT.as_posix()}/local.db"

    # Manifest database is read-only mode
    manifest_uri = f"file:{MANIFEST_PATH.as_posix()}?mode=ro"

    engine = create_engine(
        local_uri, connect_args={"check_same_thread": False, "uri": True}
    )

    @event.listens_for(engine, "connect")
    def _attach_manifest(dbapi_conn, _):
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

    created_new = False
    # No tables returned means the file has just been created and needs to be initialized with tables
    if not rows:
        LocalBase.metadata.create_all(engine)
        created_new = True

    return engine, created_new


def _seed_db(db: DB):
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
        copy_metrics_from_manifest_to_local(db)


def copy_metrics_from_manifest_to_local(db) -> int:
    """
    Copies rows from manifest.global_metrics into local_metrics
    for event_ids that exist in local_swipe_event with present == True.

    Returns number of rows attempted/affected (SQLite reports rowcount best-effort).

    Generated by ChatGPT 5.2 with the following prompt:
    -------------------------------------------------
    Write a function that copies rows from manifest.global_metrics into local_metrics
    for event_ids that exist in local_swipe_event with present == True.
    """
    with db._get_session() as session:
        # event_ids that exist locally and are marked present
        local_event_ids = select(LocalSwipeEvent.event_id).where(
            LocalSwipeEvent.present.is_(True)
        )

        # rows to copy from manifest.global_metrics
        src = select(
            ManifestMetrics.event_id,
            ManifestMetrics.avg_bbox_size,
            ManifestMetrics.step_count,
        ).where(ManifestMetrics.event_id.in_(local_event_ids))

        # INSERT ... SELECT ... with ON CONFLICT(event_id) DO UPDATE
        insert_stmt = sqlite_insert(LocalMetrics).from_select(
            ["event_id", "average_bounding_box_size", "step_count"],
            src,
        )
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=[LocalMetrics.event_id],
            set_={
                "average_bounding_box_size": insert_stmt.excluded.average_bounding_box_size,
                "step_count": insert_stmt.excluded.step_count,
            },
        )

        result = session.execute(stmt)
        # session.commit() is handled by your context manager
        return int(result.rowcount or 0)
