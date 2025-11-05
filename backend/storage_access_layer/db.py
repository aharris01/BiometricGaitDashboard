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
import datetime

load_dotenv()


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
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
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
    dsn = os.environ.get("DATABASE_URL")

    engine = create_engine(dsn)

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
