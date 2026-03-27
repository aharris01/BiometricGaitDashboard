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

    avg_bbox_size: Mapped[int] = mapped_column(Integer, nullable=False)
    std_dev_bounding_box_area: Mapped[Float] = mapped_column(Float, nullable=True)
    variance_bounding_box_area: Mapped[int] = mapped_column(Integer, nullable=True)
    mean_width: Mapped[int] = mapped_column(Integer, nullable=True)
    mean_height: Mapped[int] = mapped_column(Integer, nullable=True)
    variance_bounding_box_width: Mapped[int] = mapped_column(Integer, nullable=True)
    variance_bounding_box_height: Mapped[int] = mapped_column(Integer, nullable=True)

    step_count: Mapped[int] = mapped_column(Integer, nullable=False)
    step_count_on_path: Mapped[int] = mapped_column(Integer, nullable=True)
    total_trial_area: Mapped[Float] = mapped_column(Float, nullable=True)
    mean_step_distance: Mapped[Float] = mapped_column(Float, nullable=True)
    variance_step_distance: Mapped[int] = mapped_column(Integer, nullable=True)
    active_trial_duration_all: Mapped[Float] = mapped_column(Float, nullable=True)
    active_trial_duration_path: Mapped[Float] = mapped_column(Float, nullable=True)
    max_footstep_duration_frames: Mapped[int] = mapped_column(Integer, nullable=True)

    mean_heading_angle: Mapped[int] = mapped_column(Integer, nullable=True)
    std_heading_angle: Mapped[int] = mapped_column(Integer, nullable=True)
    variance_heading_angle: Mapped[int] = mapped_column(Integer, nullable=True)


class ManifestFootstep(ManifestBase):
    __tablename__ = "footsteps"
    __table_args__ = {"schema": "manifest"}

    event_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )

    footstep_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    start_frame: Mapped[int] = mapped_column(Integer, nullable=False)
    end_frame: Mapped[int] = mapped_column(Integer, nullable=False)

    x_min: Mapped[int] = mapped_column(Integer, nullable=False)
    x_max: Mapped[int] = mapped_column(Integer, nullable=False)
    y_min: Mapped[int] = mapped_column(Integer, nullable=False)
    y_max: Mapped[int] = mapped_column(Integer, nullable=False)


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

    avg_bbox_size: Mapped[int] = mapped_column(Integer, nullable=False)
    std_dev_bounding_box_area: Mapped[Float] = mapped_column(Float, nullable=True)
    variance_bounding_box_area: Mapped[int] = mapped_column(Integer, nullable=True)
    mean_width: Mapped[int] = mapped_column(Integer, nullable=True)
    mean_height: Mapped[int] = mapped_column(Integer, nullable=True)
    variance_bounding_box_width: Mapped[int] = mapped_column(Integer, nullable=True)
    variance_bounding_box_height: Mapped[int] = mapped_column(Integer, nullable=True)

    step_count: Mapped[int] = mapped_column(Integer, nullable=False)
    step_count_on_path: Mapped[int] = mapped_column(Integer, nullable=True)
    total_trial_area: Mapped[Float] = mapped_column(Float, nullable=True)
    mean_step_distance: Mapped[Float] = mapped_column(Float, nullable=True)
    variance_step_distance: Mapped[int] = mapped_column(Integer, nullable=True)
    active_trial_duration_all: Mapped[Float] = mapped_column(Float, nullable=True)
    active_trial_duration_path: Mapped[Float] = mapped_column(Float, nullable=True)
    max_footstep_duration_frames: Mapped[int] = mapped_column(Integer, nullable=True)

    mean_heading_angle: Mapped[int] = mapped_column(Integer, nullable=True)
    std_heading_angle: Mapped[int] = mapped_column(Integer, nullable=True)
    variance_heading_angle: Mapped[int] = mapped_column(Integer, nullable=True)


class LocalFootstep(LocalBase):
    __tablename__ = "local_footsteps"

    # This mirrors manifest.footsteps so the app can query local, writable
    # footstep rows instead of reading directly from the read-only manifest DB.
    event_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )

    footstep_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    start_frame: Mapped[int] = mapped_column(Integer, nullable=False)
    end_frame: Mapped[int] = mapped_column(Integer, nullable=False)

    x_min: Mapped[int] = mapped_column(Integer, nullable=False)
    x_max: Mapped[int] = mapped_column(Integer, nullable=False)
    y_min: Mapped[int] = mapped_column(Integer, nullable=False)
    y_max: Mapped[int] = mapped_column(Integer, nullable=False)

    step_archive_key: Mapped[int] = mapped_column(Integer, nullable=False)

    # Local-only optional label. This supports future manual review/editing
    # without changing the immutable manifest database.
    label: Mapped[str | None] = mapped_column(String, nullable=True)


class LocalFootstepChange(LocalBase):
    __tablename__ = "local_footstep_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    event_id: Mapped[str] = mapped_column(String, nullable=False)
    footstep_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # For now this will always be "edit".
    # Later this can also support "create" and "delete".
    action: Mapped[str] = mapped_column(String, nullable=False)

    changed_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        default=datetime.datetime.utcnow,
    )

    old_x_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    old_x_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    old_y_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    old_y_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    old_start_frame: Mapped[int | None] = mapped_column(Integer, nullable=True)
    old_end_frame: Mapped[int | None] = mapped_column(Integer, nullable=True)
    old_label: Mapped[str | None] = mapped_column(String, nullable=True)

    new_x_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_x_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_y_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_y_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_start_frame: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_end_frame: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_label: Mapped[str | None] = mapped_column(String, nullable=True)
