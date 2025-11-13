import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import Date
from sqlalchemy import Integer
from sqlalchemy import TIMESTAMP
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import datetime

from sqlalchemy import select, distinct

load_dotenv()

dataroot = os.environ.get("DATAROOT")
if dataroot is None:
    dataroot = "./data"

class Base(DeclarativeBase):
    pass


class SwipeEvent(Base):
    __tablename__ = "swipe_event"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)

    participant: Mapped[int] = mapped_column(Integer, nullable=False)

    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)

    direction: Mapped[str] = mapped_column(String, nullable=False)

    event_number: Mapped[int] = mapped_column(Integer, nullable=False)

    state: Mapped[str] = mapped_column(String, nullable=False)

    trial_npz_uri: Mapped[str] = mapped_column(Text, nullable=False)

    trial_p100_npz_uri: Mapped[str] = mapped_column(Text, nullable=False)

    trial_grf_npz_uri: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.datetime.now(),   # <--- Python-side default (portable)
    )

#adding a db class here that holds db engine and access functions. functions still accessable through accessfunctions.py 
class DB:

    def __init__(self, engine=None):
        self.engine = engine or _initDB()
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

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

    # Original addSwipeEvent function with parameters
    def addSwipeEvent(self,
        event_id,
        participant,
        date,
        direction,
        event_number,
        state,
        trial_npz_uri,
        trial_p100_npz_uri,
        trial_grf_npz_uri,
    ):

        swipe_event = SwipeEvent(
            event_id=event_id,
            participant=participant,
            date=date,
            direction=direction,
            event_number=event_number,
            state=state,
            trial_npz_uri=trial_npz_uri,
            trial_p100_npz_uri=trial_p100_npz_uri,
            trial_grf_npz_uri=trial_grf_npz_uri,
        )

        with self._get_session() as session:
            try:
                session.add(swipe_event)
            except:
                print("Duplicate found")

    # New addSwipeEvent function that accepts a SwipeEvent object
    def addSwipeEvent(self, swipe_event: SwipeEvent):
        with self._get_session() as session:
            try:
                session.add(swipe_event)
            except:
                print("Duplicate found")

    # identical logic to previous version of accessfunctions.py
    def getParticipants(self):
        query = select(distinct(SwipeEvent.participant)).order_by(SwipeEvent.participant)
        
        with self._get_session() as session:
            return session.scalars(query).all()

    def getDates(self, participant):
        query = (
            select(distinct(SwipeEvent.date))
            .where(SwipeEvent.participant == participant)
            .order_by(SwipeEvent.date)
        )
        
        with self._get_session() as session:
            return session.scalars(query).all()

    def getDirections(self, participant, date):
        query = (
            select(distinct(SwipeEvent.direction))
            .where(SwipeEvent.participant == participant, SwipeEvent.date == date)
            .order_by(SwipeEvent.direction)
        )
        with self._get_session() as session:
            return session.scalars(query).all()

    def getEvents(self, participant, date, direction):
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
        
    def getSwipeEventId(self, participant, date, event, direction):
        query = (
            select(SwipeEvent.event_id)
            .where(
                SwipeEvent.participant == participant,
                SwipeEvent.date == date,
                SwipeEvent.event_number == event,
                SwipeEvent.direction == direction,
            )
        )

        with self._get_session() as session:
            return session.scalars(query).first()

    def getBothDirectionEvents(self, participant, date):
        directions = self.getDirections(participant, date)
        return [self.getEvents(participant, date, d) for d in directions]


def _initDB(): #added function as required 
    engine = create_engine(f"sqlite:///{dataroot}/metadata.db")

    # check existing tables
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table';") #added logic for table search 
        ).fetchall()

    if len(rows) == 0:
        Base.metadata.create_all(engine)

    return engine