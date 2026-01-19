from sqlalchemy import String, Text, Date, Integer, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import datetime


class ManifestBase(DeclarativeBase):
    pass


class SwipeEvent(ManifestBase):
    __tablename__ = "swipe_event"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    participant: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    direction: Mapped[str] = mapped_column(String, nullable=False)
    event_number: Mapped[int] = mapped_column(Integer, nullable=False)
    local: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
