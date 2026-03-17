from datetime import date

from backend.storage_access_layer.pipeline.footstep_edits import FootstepEditor
from backend.scripts.calc_metrics import calculate_all_metrics
from backend.storage_access_layer.utils import uri_to_path

from ..db.db import DB
from ..utils.types import (
    FootstepReviewPayload,
    ReviewBBoxPayload,
    ReviewChangePayload,
    FootstepSearchFilters,
    FootstepSearchItem,
    ReviewItemPayload,
)
from .common import CommonHelper


class SalFootsteps:
    def __init__(self, db: DB, common: CommonHelper):
        self.db = db
        self.common = common
        self.editor = FootstepEditor(db, common)

    def search_footsteps(
        self, filters: FootstepSearchFilters
    ) -> dict[str, list[FootstepSearchItem] | int]:

        rows, total = self.db.search_footsteps(
            event_ids=filters.event_ids,
            participants=filters.participants,
            date_from=filters.date_from,
            date_to=filters.date_to,
            width_min=filters.width_min,
            width_max=filters.width_max,
            height_min=filters.height_min,
            height_max=filters.height_max,
            size_min=filters.size_min,
            size_max=filters.size_max,
            offset=filters.offset,
            limit=filters.limit,
        )

        items = [_map_search_row(row) for row in rows]

        return {"items": items, "total": total}

    def get_footsteps(self, event_id: str):
        _event, err = self.common._require_event(event_id)
        if err:
            return None, err

        rows = self.db.get_event_footsteps(event_id)

        steps: list[dict] = []
        for row in rows:
            steps.append(
                {
                    "id": int(row.footstep_id),
                    "start_frame": int(row.start_frame),
                    "end_frame": int(row.end_frame),
                    "x_min": int(row.x_min),
                    "x_max": int(row.x_max),
                    "y_min": int(row.y_min),
                    "y_max": int(row.y_max),
                }
            )
        if len(steps) == 0:
            return None, "missing_footsteps"

        return steps, None

    # -------------------------------------------------
    # Footstep view DB for single footstep. To be added
    # to "get_footsteps()" for refactor allowing for faster
    # summary view footstep performance
    # -------------------------------------------------
    def get_single_footstep(self, event_id: str, footstep_id: int):
        _event, err = self.common._require_event(event_id)
        if err:
            return None, err

        # Keep database access behind the DB layer. The DB implementation decides
        # whether the underlying footstep row comes from local.db or manifest.db.
        row = self.db.get_single_footstep(event_id, footstep_id)

        if row is None:
            return None, "no_footstep"

        return (
            {
                "id": row.footstep_id,
                "start_frame": row.start_frame,
                "end_frame": row.end_frame,
                "x_min": row.x_min,
                "x_max": row.x_max,
                "y_min": row.y_min,
                "y_max": row.y_max,
            },
            None,
        )

    # Build the review payload for one footstep.
    #
    # Important:
    # - the selected footstep still comes from the Footsteps view thumbnail
    # - review/editing happens on the full event p100 image
    # - bbox, label, and frame values come from local.db
    # - local edit history is included from the changelog table
    #
    # This payload is the single source used by the frontend review panel.

    def get_footstep_review_context(self, event_id: str, footstep_id: int):
        _event, err = self.common._require_event(event_id)
        if err:
            return None, err

        footstep, footstep_err = self.common._require_footstep(event_id, footstep_id)
        if footstep_err or footstep is None:
            return None, footstep_err

        p100, p100_err = self.common._get_p100(event)
        if p100_err or p100 is None:
            return None, p100_err

        changes: list[ReviewChangePayload] = []
        for change in self.db.get_local_footstep_changes(event_id, footstep_id):
            changes.append(
                {
                    "action": change.action,
                    "changed_at": change.changed_at.isoformat(
                        sep=" ", timespec="seconds"
                    ),
                    "old_x_min": change.old_x_min,
                    "old_x_max": change.old_x_max,
                    "old_y_min": change.old_y_min,
                    "old_y_max": change.old_y_max,
                    "old_start_frame": change.old_start_frame,
                    "old_end_frame": change.old_end_frame,
                    "old_label": change.old_label,
                    "new_x_min": change.new_x_min,
                    "new_x_max": change.new_x_max,
                    "new_y_min": change.new_y_min,
                    "new_y_max": change.new_y_max,
                    "new_label": change.new_label,
                    "new_start_frame": change.new_start_frame,
                    "new_end_frame": change.new_end_frame,
                }
            )

        payload = FootstepReviewPayload(
            item=ReviewItemPayload(
                event_id=event_id,
                footstep_id=int(footstep.footstep_id),
                start_frame=footstep.start_frame,
                end_frame=footstep.end_frame,
                label=footstep.label,
            ),
            bbox=ReviewBBoxPayload(
                x_min=int(footstep.x_min),
                x_max=int(footstep.x_max),
                y_min=int(footstep.y_min),
                y_max=int(footstep.y_max),
            ),
            event_p100=p100,
            changes=changes,
        )

        return payload, None

    def save_footstep_review(self, event_id: str, footstep_id: int, edits: dict):
        # Validate and save one local footstep edit.
        #
        # Validation is done here because the SAL knows the real event image
        # bounds and keeps write behavior behind the DB layer. This updates the
        # current local footstep row and lets the DB layer write the matching
        # changelog entry for the edit.

        # Validate the event exists
        event, event_err = self.common._require_event(event_id)
        if event_err or event is None:
            return None, event_err

        review, err = self.get_footstep_review_context(event_id, footstep_id)
        if err:
            return None, err

        if review is None:
            return None, "missing_file"

        bbox_valid, valid_err = _validate_bounding_box(
            edits["x_min"],
            edits["x_max"],
            edits["y_min"],
            edits["y_max"],
            edits["start_frame"],
            edits["end_frame"],
            review["event_p100"],
            self.common,
        )

        if valid_err or not bbox_valid:
            return None, valid_err

        if edits["label"] is not None:
            label = str(edits["label"]).strip() or None
            edits["label"] = label

        edit_ok, edit_err = self.editor.edit_footstep(
            footstep_id,
            event_id,
            {
                "XMin": edits["x_min"],
                "XMax": edits["x_max"],
                "YMin": edits["y_min"],
                "YMax": edits["y_max"],
                "StartFrame": edits["start_frame"],
                "EndFrame": edits["end_frame"],
            },
        )

        if edit_err or not edit_ok:
            return None, edit_err or "edit_failed"

        try:
            updated = self.db.update_local_footstep(event_id, footstep_id, edits)
        except ValueError:
            return None, "invalid_change"

        if updated is None:
            return None, "no_footstep"

        event_metadata_path = uri_to_path(event.trial_npz_uri).parent / "metadata.csv"
        new_metrics, metrics_err = calculate_all_metrics(event_id, event_metadata_path)

        if metrics_err or new_metrics is None:
            return None, "calculation_error"

        result = self.db.update_event_metrics(event_id, new_metrics)

        if result is None:
            return None, "unexpected_error"

        return self.get_footstep_review_context(event_id, footstep_id)

    def create_footstep(
        self,
        event_id: str,
        *,
        start_frame: int,
        end_frame: int,
        x_min: int,
        x_max: int,
        y_min: int,
        y_max: int,
        label: str | None,
    ):
        event, err = self.common._require_event(event_id)
        if err or event is None:
            return None, err

        p100, p100_err = self.common._get_p100(event)
        if p100_err:
            return None, p100_err

        frame_count, err = self.common._get_trial_frame_count(event)
        if err or frame_count is None:
            return None, err

        start_frame = int(start_frame)
        end_frame = int(end_frame)
        x_min = int(x_min)
        x_max = int(x_max)
        y_min = int(y_min)
        y_max = int(y_max)

        bbox_valid, valid_err = _validate_bounding_box(
            x_min, x_max, y_min, y_max, start_frame, end_frame, p100, self.common
        )
        if valid_err or not bbox_valid:
            return None, valid_err

        if label is not None:
            label = str(label).strip() or None

        created = self.db.create_local_footstep(
            event_id,
            start_frame=start_frame,
            end_frame=end_frame,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
            label=label,
        )
        if created is None:
            return None, "missing_file"

        return self.get_footstep_review_context(event_id, int(created.footstep_id))

    def delete_footstep(self, event_id: str, footstep_id: int):
        event, err = self.common._require_event(event_id)
        if err:
            return None, err

        row = self.db.get_single_footstep(event_id, footstep_id)
        if row is None:
            return None, "missing_file"

        deleted = self.db.delete_local_footstep(event_id, footstep_id)
        if deleted is None:
            return None, "missing_file"

        return {
            "ok": True,
            "event_id": event_id,
            "footstep_id": footstep_id,
        }, None

    def get_footstep_data(self, event_id: str, step_id: int):
        event, err = self.common._require_event(event_id)
        if err:
            return None, None, err

        steps_npz, steps_err = self.common._load_steps_npz(event)
        if steps_err or steps_npz is None:
            return None, None, steps_err

        key = str(step_id)
        if key not in steps_npz.files:
            return None, None, "missing_file"

        # vol is the full footstep pressure volume across time.
        # Shape: (time, height, width)
        vol = steps_npz[key]  # (T, H, W)

        # step_p100 is the max pressure image for this footstep.
        # This is used for footstep heatmap-style rendering.
        step_p100 = vol.max(axis=0)  # (H, W)

        # step_grf is the per-frame total pressure signal.
        # This is used like a simple force-over-time curve.
        step_grf = vol.reshape(vol.shape[0], -1).sum(axis=1)  # (T,)

        return step_p100, step_grf.tolist(), None

    # Return the max-pressure image for every footstep in one event.
    # This is mainly used by the summary view when many footsteps
    # need to be shown without loading each one separately.

    def get_all_footstep_p100(self, event_id: str):
        event, err = self.common._require_event(event_id)
        if err:
            return None, err

        steps_npz, steps_err = self.common._load_steps_npz(event)
        if steps_err or steps_npz is None:
            return None, steps_err

        items = []
        try:
            for key in steps_npz.files:
                vol = steps_npz[key]  # (T, H, W)
                step_p100 = vol.max(axis=0)  # (H, W)
                items.append({"id": int(key), "p100": step_p100.tolist()})
        except Exception:
            return None, "missing_file"

        items.sort(key=lambda x: x["id"])
        return items, None

    # Return both the max-pressure image and force-over-time data
    # for every footstep in one event.
    #
    # This is a heavier helper than get_all_footstep_p100() and is
    # meant for views that need both visual and time-series data.

    def get_all_footstep_details(self, event_id: str):
        event, err = self.common._require_event(event_id)
        if err:
            return None, err

        steps_npz, steps_err = self.common._load_steps_npz(event)
        if steps_err or steps_npz is None:
            return None, steps_err

        items = []
        try:
            for key in steps_npz.files:
                vol = steps_npz[key]  # (T, H, W)
                step_p100 = vol.max(axis=0)  # (H, W)
                step_grf = vol.reshape(vol.shape[0], -1).sum(axis=1)  # (T,)
                items.append(
                    {
                        "id": int(key),
                        "p100": step_p100.tolist(),
                        "grf": step_grf.tolist(),
                    }
                )
        except Exception:
            return None, "missing_file"

        items.sort(key=lambda x: x["id"])
        return items, None


def _normalize_search_filters(
    event_ids: list[str] | None = None,
    participants: list[int] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    width_min: int | None = None,
    width_max: int | None = None,
    height_min: int | None = None,
    height_max: int | None = None,
    size_min: int | None = None,
    size_max: int | None = None,
    offset: int = 0,
    limit: int = 60,
) -> FootstepSearchFilters:
    norm_ids = [str(x) for x in event_ids if x] if event_ids else None
    norm_parts = [int(x) for x in participants] if participants else None

    offset = max(0, int(offset))
    limit = max(1, min(int(limit), 200))

    if width_min is not None and width_max is not None and width_min > width_max:
        raise ValueError("width_min must be <= width_max")
    if height_min is not None and height_max is not None and height_min > height_max:
        raise ValueError("height_min must be <= height_max")
    if size_min is not None and size_max is not None and size_min > size_max:
        raise ValueError("size_min must be <= size_max")
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ValueError("date_from must be <= date_to")

    return FootstepSearchFilters(
        event_ids=norm_ids,
        participants=norm_parts,
        date_from=date_from,
        date_to=date_to,
        width_min=width_min,
        width_max=width_max,
        height_min=height_min,
        height_max=height_max,
        size_min=size_min,
        size_max=size_max,
        offset=offset,
        limit=limit,
    )


def _map_search_row(row) -> FootstepSearchItem:
    return {
        "event_id": row["event_id"],
        "footstep_id": int(row["footstep_id"]),
        "participant": row["participant"],
        "date": row["date"].isoformat() if row["date"] is not None else None,
        "start_frame": int(row["start_frame"]),
        "end_frame": int(row["end_frame"]),
        "x_min": int(row["x_min"]),
        "x_max": int(row["x_max"]),
        "y_min": int(row["y_min"]),
        "y_max": int(row["y_max"]),
        "bbox_width": int(row["bbox_width"]),
        "bbox_height": int(row["bbox_height"]),
        "bbox_area": int(row["bbox_area"]),
        "has_thumbnail": bool(row["has_thumbnail"]),
    }


def _validate_bounding_box(
    x_min: int,
    x_max: int,
    y_min: int,
    y_max: int,
    start_frame: int,
    end_frame: int,
    p100,
    common: CommonHelper,
):
    image_width, image_height, dim_err = common._get_image_dims(p100)
    if dim_err or image_width is None or image_height is None:
        return False, dim_err

    if x_min < 0 or y_min < 0:
        return False, "invalid_bbox"

    if x_min >= x_max or y_min >= y_max:
        return False, "invalid_bbox"

    if x_max > image_width or y_max > image_height:
        return False, "invalid_bbox"

    if 0 > start_frame > 3000 or 0 > end_frame > 3000:
        return False, "invalid_bbox"

    if start_frame >= end_frame:
        return False, "invalid_bbox"

    return True, None
