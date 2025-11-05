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
    #small modification made here to help with sql lite temp server compatability with postgres syntax -jon
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP" if os.environ.get("DATABASE_URL", "").startswith("sqlite") else "now()") #only for pytest to help CI -jon
    )
    


dsn = os.environ.get("DATABASE_URL")

#just added this so I could use sql lite to run my pytest -jon
if dsn:
    engine = create_engine(dsn)
else:
    engine = create_engine("sqlite:///:memory:") 

participant = 1
date = datetime.date(2025, 1, 1)
direction = "in"
event_number = 1
state = "ready"

swipe_event = SwipeEvent(
    event_id="001_2025-01-01_in_1_ready",
    participant=participant,
    date=date,
    direction=direction,
    event_number=event_number,
    state=state,
    trial_npz_uri=f"file://{participant}/{date}/{direction}/{event_number}/trial.npz",
    trial_p100_npz_uri=f"file://{participant}/{date}/{direction}/{event_number}/trial.p100.npz",
    trial_grf_npz_uri=f"file://{participant}/{date}/{direction}/{event_number}/trial.grf.npz",
)
# needed to add this too so that I can use the swipe event class in my functions -jon
if __name__ == "__main__": 
    with Session(engine) as session:
        session.add(swipe_event)
        session.commit()
