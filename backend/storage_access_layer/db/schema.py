from sqlalchemy import String, Text, Date, Integer, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import datetime


class ManifestBase(DeclarativeBase):
    pass


class ManifestSwipeEvent(ManifestBase):
    __tablename__ = "swipe_event"
    __table_args__ = {"schema": "manifest"}

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    participant: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    direction: Mapped[str] = mapped_column(String, nullable=False)
    event_number: Mapped[int] = mapped_column(Integer, nullable=False)
    local: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class LocalBase(DeclarativeBase):
    pass


class LocalSwipeEvent(LocalBase):
    __tablename__ = "local_swipe_event"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    root_path: Mapped[str] = mapped_column(String, nullable=False)

    # These columns are to determine if there are any changes to the available data
    present: Mapped[int] = mapped_column(Integer, nullable=False)
    last_seen: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, nullable=False)
