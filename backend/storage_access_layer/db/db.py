# backend/storage_access_layer/db.py
import os
from pathlib import Path
from dotenv import load_dotenv

from sqlalchemy import Engine, create_engine, event, exists, and_
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker, with_loader_criteria, Session
from contextlib import contextmanager
from sqlalchemy import select, distinct
from .schema import LocalBase, LocalSwipeEvent, ManifestSwipeEvent

from ...scripts.ingest import iter_swipes

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = PROJECT_ROOT / "manifest.db"

dataroot = os.environ.get("DATAROOT", ".")  # Defaults to root


def apply_local_filter(query):
    return query.where(
        exists().where(
            and_(
                LocalSwipeEvent.event_id == ManifestSwipeEvent.event_id,
                LocalSwipeEvent.present.is_(True),
            )
        )
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
        query = apply_local_filter(
            select(ManifestSwipeEvent).where(ManifestSwipeEvent.event_id == event_id)
        )
        with self._get_session() as session:
            return session.scalars(query).first()


# -------------------------------------------------
# DB initialisation helpers
# -------------------------------------------------


def _init_db():
    # Local database is writable
    local_uri = f"sqlite:///{dataroot}/local.db"

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
            (f"file:{MANIFEST_PATH.as_posix()}?mode=ro",),
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
    for swipe_data in iter_swipes(Path(dataroot)):
        swipe_event_obj = LocalSwipeEvent(**swipe_data)
        db.add_swipe_event(swipe_event_obj)
