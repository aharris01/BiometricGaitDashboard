from __future__ import annotations

from typing import Any, TypeAlias, TypeVar, Literal

import numpy as np

from ..db.db import DB
from ..db.models import SwipeEvent
from ..db.schema import LocalFootstep
from ..utils import uri_to_path

ErrorCode: TypeAlias = Literal["missing_event", "missing_file", "invalid_footstep"]
T = TypeVar("T")
Result: TypeAlias = tuple[T | None, ErrorCode | None]


class CommonHelper:
    def __init__(self, db: DB):
        self.db = db

    def _require_event(self, event_id: str) -> Result[SwipeEvent]:
        event = self.db.get_swipe_event(event_id)
        if event is None:
            return None, "missing_event"
        return event, None

    def _require_footstep(
        self, event_id: str, footstep_id: int
    ) -> Result[LocalFootstep]:
        footstep = self.db.get_single_footstep(event_id, footstep_id)
        if footstep is None:
            return None, "invalid_footstep"

        return footstep, None

    def _load_npz_from_uri(self, uri: str, key: str = "arr_0") -> Result[np.ndarray]:
        try:
            file_path = uri_to_path(uri)
            loaded = np.load(file_path)
        except Exception:
            return None, "missing_file"

        try:
            if hasattr(loaded, "files"):
                if key in loaded.files:
                    arr = loaded[key]
                elif loaded.files:
                    arr = loaded[loaded.files[0]]
                else:
                    return None, "missing_file"
            else:
                arr = loaded
        except Exception:
            return None, "missing_file"

        if not isinstance(arr, np.ndarray):
            return None, "missing_file"
        return arr, None

    def _load_steps_npz(self, event: Any):
        try:
            trial_path = uri_to_path(event.trial_npz_uri)
        except ValueError:
            return None, "missing_file"

        steps_path = trial_path.with_name("steps.npz")
        if not steps_path.exists():
            return None, "missing_file"

        try:
            return np.load(steps_path), None
        except Exception:
            return None, "missing_file"

    def _get_trial_frame_count(self, event: SwipeEvent):
        array, arr_err = self._load_npz_from_uri(event.trial_grf_npz_uri, key="[:,:]")
        if arr_err or array is None:
            return None, arr_err

        if getattr(array, "ndim", 0) < 1:
            return None, "missing_file"

        return int(array.shape[0]), None

    def _get_p100(self, event: SwipeEvent):
        array, arr_err = self._load_npz_from_uri(event.trial_p100_npz_uri, key="arr_0")
        if arr_err or array is None:
            return None, "missing_p100"

        return array, None

    def _get_image_dims(self, p100: np.ndarray):
        image_height, image_width = p100.shape
        if image_width <= 0 or image_height <= 0:
            return None, None, "invalid_img_dimensions"

        return image_width, image_height, None
