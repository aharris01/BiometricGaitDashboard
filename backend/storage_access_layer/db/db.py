# backend/storage_access_layer/db.py
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine
from sqlalchemy import String, Text, Date, Integer, TIMESTAMP, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from contextlib import contextmanager
import datetime

from sqlalchemy import select, distinct
from ...scripts.ingest import iter_swipes

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = PROJECT_ROOT / "manifest.db"

dataroot = os.environ.get("DATAROOT", ".")  # Defaults to root


class Base(DeclarativeBase):
    pass


class SwipeEvent(Base):
    __tablename__ = "swipe_event"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    participant: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    direction: Mapped[str] = mapped_column(String, nullable=False)
    event_number: Mapped[int] = mapped_column(Integer, nullable=False)
    local: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


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

    # New add_swipe_event function that accepts a SwipeEvent object
    def add_swipe_event(self, swipe_event_obj: SwipeEvent):
        with self._get_session() as session:
            try:
                session.add(swipe_event_obj)
            except Exception as e:
                print(f"{e}: Duplicate found")

    # identical logic to previous version of accessfunctions.py
    def get_participants(self):
        query = select(distinct(SwipeEvent.participant)).order_by(
            SwipeEvent.participant
        )
        with self._get_session() as session:
            return session.scalars(query).all()

    def get_dates(self, participant):
        query = (
            select(distinct(SwipeEvent.date))
            .where(SwipeEvent.participant == participant)
            .order_by(SwipeEvent.date)
        )
        with self._get_session() as session:
            return session.scalars(query).all()

    def get_directions(self, participant, date):
        query = (
            select(distinct(SwipeEvent.direction))
            .where(
                SwipeEvent.participant == participant,
                SwipeEvent.date == date,
            )
            .order_by(SwipeEvent.direction)
        )
        with self._get_session() as session:
            return session.scalars(query).all()

    def get_events(self, participant, date, direction):
        query = (
            select(distinct(SwipeEvent.event_number))
            .where(
                SwipeEvent.participant == participant,
                SwipeEvent.date == date,
                SwipeEvent.direction == direction,
            )
            .order_by(SwipeEvent.event_number)
        )
        with self._get_session() as session:
            return session.scalars(query).all()

    def get_swipe_event_id(self, participant, date, event, direction):
        query = select(SwipeEvent.event_id).where(
            SwipeEvent.participant == participant,
            SwipeEvent.date == date,
            SwipeEvent.event_number == event,
            SwipeEvent.direction == direction,
        )
        with self._get_session() as session:
            return session.scalars(query).first()

    def get_swipe_event(self, event_id):
        query = select(SwipeEvent).where(SwipeEvent.event_id == event_id)
        with self._get_session() as session:
            return session.scalars(query).first()


# -------------------------------------------------
# DB initialisation helpers
# -------------------------------------------------


def _init_db():
    engine = create_engine(f"sqlite:///{MANIFEST_PATH}")

    # Check if the database file is being created for the first time by querying which tables exist
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table';")
        ).fetchall()

    created_new = False
    # No tables returned means the file has just been created and needs to be initialized with tables
    if not rows:
        Base.metadata.create_all(engine)
        created_new = True

    return engine, created_new


def _seed_db(db: DB):
    for swipe_data in iter_swipes(Path(dataroot)):
        swipe_event_obj = SwipeEvent(**swipe_data)
        db.add_swipe_event(swipe_event_obj)
