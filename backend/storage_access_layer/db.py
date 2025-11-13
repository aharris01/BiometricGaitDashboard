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
if dataroot:  # just added this so I could use sql lite to run my pytest -jon
    engine = create_engine(f"sqlite:///{dataroot}/metadata.db")
else:
    engine = create_engine("sqlite:///:memory:")

# added a session helper function to limit coupling between layers

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


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
        default=datetime.datetime.utcnow,   # <--- Python-side default (portable)
    )


def addSwipeEvent(
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

    with Session(engine) as session:
        try:
            session.add(swipe_event)
            session.commit()
        except:
            print("Duplicate found")


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

#adding a db class here that holds db engine and access functions. functions still accessable through accessfunctions.py 
class DB:

    def __init__(self, engine):
        self.engine = engine

    # identical logic to previous version of accessfunctions.py
    def getParticipants(self, session):
        query = select(distinct(SwipeEvent.participant)).order_by(SwipeEvent.participant)
        return session.scalars(query).all()

    def getDates(self, session, participant):
        query = (
            select(distinct(SwipeEvent.date))
            .where(SwipeEvent.participant == participant)
            .order_by(SwipeEvent.date)
        )
        return session.scalars(query).all()

    def getDirections(self, session, participant, date):
        query = (
            select(distinct(SwipeEvent.direction))
            .where(SwipeEvent.participant == participant, SwipeEvent.date == date)
            .order_by(SwipeEvent.direction)
        )
        return session.scalars(query).all()

    def getEvents(self, session, participant, date, direction):
        query = (
            select(distinct(SwipeEvent.event_number))
            .where(
                SwipeEvent.participant == participant,
                SwipeEvent.date == date,
                SwipeEvent.direction == direction,
            )
            .order_by(SwipeEvent.event_number)
        )
        return session.scalars(query).all()

    def getSwipeEventId(self, session, participant, date, event, direction):
        query = (
            select(SwipeEvent.event_id)
            .where(
                SwipeEvent.participant == participant,
                SwipeEvent.date == date,
                SwipeEvent.event_number == event,
                SwipeEvent.direction == direction,
            )
        )
        return session.scalars(query).first()

    def getBothDirectionEvents(self, session, participant, date):
        directions = self.getDirections(session, participant, date)
        return [self.getEvents(session, participant, date, d) for d in directions]


def initDB(seed_function=None): #added function as required 
    db = DB(engine)

    # check existing tables
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table';") #added logic for table search 
        ).fetchall()

    if len(rows) == 0:
        Base.metadata.create_all(engine)
        if seed_function:
            seed_function(db)

    return db
