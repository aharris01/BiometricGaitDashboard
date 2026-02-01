from sqlalchemy import String, Date, Integer, TIMESTAMP, Float
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


class ManifestMetrics(ManifestBase):
    __tablename__ = "global_metrics"
    __table_args__ = {"schema": "manifest"}

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    average_bounding_box_size: Mapped[Float] = mapped_column(Float, nullable=True)
    step_count: Mapped[int] = mapped_column(Integer, nullable=True)


class LocalBase(DeclarativeBase):
    pass


class LocalSwipeEvent(LocalBase):
    __tablename__ = "local_swipe_event"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    root_path: Mapped[str] = mapped_column(String, nullable=False)

    # These columns are to determine if there are any changes to the available data
    present: Mapped[int] = mapped_column(Integer, nullable=False)
    last_seen: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, nullable=False)


class LocalMetrics(LocalBase):
    __tablename__ = "local_metrics"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    average_bounding_box_size: Mapped[Float] = mapped_column(Float, nullable=True)
    step_count: Mapped[int] = mapped_column(Integer, nullable=True)
