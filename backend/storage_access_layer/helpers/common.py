from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
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
        self._trial_recording_cache_dir = (
            Path(tempfile.gettempdir()) / "biometric_gait_dashboard"
        )
        self._trial_recording_cache_ttl_seconds = 24 * 60 * 60

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

    def _get_trial_recording_cache_path(self, event_id: str) -> Path:
        return self._trial_recording_cache_dir / f"{event_id}.trial.npy"

    def _prune_trial_recording_cache(self) -> None:
        if not self._trial_recording_cache_dir.exists():
            return

        cutoff = time.time() - self._trial_recording_cache_ttl_seconds
        for cache_path in self._trial_recording_cache_dir.glob("*.trial.npy"):
            try:
                if cache_path.stat().st_mtime < cutoff:
                    cache_path.unlink()
            except FileNotFoundError:
                continue
            except Exception:
                continue

    def _touch_trial_recording_cache(self, cache_path: Path) -> None:
        try:
            os.utime(cache_path, None)
        except Exception:
            return

    def _load_trial_recording(self, event: SwipeEvent) -> Result[np.ndarray]:
        event_id = getattr(event, "event_id", None)
        if not isinstance(event_id, str) or not event_id:
            return None, "missing_event"

        self._prune_trial_recording_cache()
        cache_path = self._get_trial_recording_cache_path(event_id)
        if cache_path.exists():
            try:
                cached = np.load(cache_path, allow_pickle=False)
            except Exception:
                pass
            else:
                if isinstance(cached, np.ndarray):
                    self._touch_trial_recording_cache(cache_path)
                    return cached, None

        array, arr_err = self._load_npz_from_uri(event.trial_npz_uri)
        if arr_err or array is None:
            return None, arr_err

        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            np.save(cache_path, array, allow_pickle=False)
        except Exception:
            return array, None

        try:
            cached = np.load(cache_path, allow_pickle=False)
        except Exception:
            return array, None

        if not isinstance(cached, np.ndarray):
            return array, None
        self._touch_trial_recording_cache(cache_path)
        return cached, None

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
