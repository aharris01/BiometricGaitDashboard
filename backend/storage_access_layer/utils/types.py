from dataclasses import dataclass
from datetime import date
from typing import TypedDict


class ReviewItemPayload(TypedDict):
    event_id: str
    footstep_id: int
    start_frame: int
    end_frame: int
    label: str | None


class ReviewBBoxPayload(TypedDict):
    x_min: int
    x_max: int
    y_min: int
    y_max: int


class ReviewChangePayload(TypedDict):
    action: str
    changed_at: str
    old_x_min: int | None
    old_x_max: int | None
    old_y_min: int | None
    old_y_max: int | None
    old_label: str | None
    new_x_min: int | None
    new_x_max: int | None
    new_y_min: int | None
    new_y_max: int | None
    new_label: str | None


class FootstepReviewPayload(TypedDict):
    item: ReviewItemPayload
    bbox: ReviewBBoxPayload
    event_p100: list[list[float]]
    image_width: int
    image_height: int
    changes: list[ReviewChangePayload]


class FootstepSearchItem(TypedDict):
    event_id: str
    footstep_id: int
    participant: int | None
    date: str | None
    start_frame: int
    end_frame: int
    x_min: int
    x_max: int
    y_min: int
    y_max: int
    bbox_width: int
    bbox_height: int
    bbox_area: int
    has_thumbnail: bool


@dataclass(frozen=True)
class FootstepSearchFilters:
    event_ids: list[str] | None = None
    participants: list[int] | None = None
    date_from: date | None = None
    date_to: date | None = None
    width_min: int | None = None
    width_max: int | None = None
    height_min: int | None = None
    height_max: int | None = None
    size_min: int | None = None
    size_max: int | None = None
    offset: int = 0
    limit: int = 60
