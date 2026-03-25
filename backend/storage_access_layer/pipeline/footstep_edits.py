from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from zipfile import ZipFile, ZIP_DEFLATED
import numpy as np

from backend.storage_access_layer.db.models import SwipeEvent
from backend.storage_access_layer.db.schema import LocalFootstep

from ..utils import uri_to_path
from ..db.db import DB
from ..helpers.common import CommonHelper
from .utils.pipeline_utils import (
    get_heading,
    load_metadata,
    identify_anchor_footstep,
    _is_within_expect_duration,
    _is_within_expected_bb_size,
    reset_path_order,
    trace_path,
)
from .utils.preprocess_footsteps import preprocess_footsteps
from flask import current_app


class FootstepEditor:
    def __init__(self, db: DB, common: CommonHelper):
        self.db = db
        self.common = common

    def edit_footstep(
        self, footstep_id: int, event_id: str, new_footstep_data: dict, p100: np.ndarray
    ):
        # ----------------------------------------------
        # Need to find a way to revert any changes if any step in the process fails, to maintain data integrity
        # ----------------------------------------------
        # validate footstep_id and event_id
        event, event_err = self.common._require_event(event_id)
        if event_err or event is None:
            return False, event_err

        footstep, footstep_err = self.common._require_footstep(event_id, footstep_id)
        if footstep_err or footstep is None:
            return False, footstep_err
        archive_key = _get_archive_key(footstep, footstep_id)

        # open metadata for the event
        trial_folder = uri_to_path(event.trial_npz_uri).parent
        try:
            metadata_file_path = trial_folder / "metadata.csv"
            metadata_df = load_metadata(metadata_file_path)
        except Exception as e:
            current_app.logger.error(f"Error loading metadata: {e}")
            return False, f"Error loading metadata: {e}"

        # make edits to footstep in df
        metadata_df.loc[
            metadata_df["FootstepID"] == archive_key,
            ["XMin", "XMax", "YMin", "YMax", "StartFrame", "EndFrame"],
        ] = [
            new_footstep_data["XMin"],
            new_footstep_data["XMax"],
            new_footstep_data["YMin"],
            new_footstep_data["YMax"],
            new_footstep_data["StartFrame"],
            new_footstep_data["EndFrame"],
        ]
        metadata_df, archive_key_updates = _reassign_footstep_ids_by_start_frame(
            metadata_df
        )
        new_archive_key = archive_key_updates[archive_key]

        # validate footstep bounding box data
        edited_row = metadata_df.loc[metadata_df["FootstepID"] == new_archive_key].iloc[
            0
        ]
        metadata_df["valid"] = metadata_df["valid"].apply(bool)
        if not _is_within_expected_bb_size(
            edited_row
        ) or not _is_within_expect_duration(edited_row):
            metadata_df.loc[metadata_df["FootstepID"] == new_archive_key, "valid"] = (
                False
            )
        else:
            metadata_df.loc[metadata_df["FootstepID"] == new_archive_key, "valid"] = (
                True
            )

        # find path order (anchor identification and path order identification)
        # print("Finding path order...")
        metadata_df["path_order"] = -1  # Any footsteps not on path will be -1
        # print("Identifying anchor footstep...")
        identify_anchor_footstep(metadata_df)

        metadata_df["heading_angle"] = metadata_df.apply(
            get_heading, args=(p100,), axis=1
        )

        metadata_df["path_order"] = metadata_df.apply(reset_path_order, axis=1)

        trace_path(metadata_df)

        metadata_df["is_anchor"] = metadata_df["path_order"] == 0
        metadata_df["is_on_path"] = metadata_df["path_order"] >= 0

        # take new bounding box data from trial recording and update steps.raw.npz and steps.npz

        # print("Opening trial recording...")
        trial_recording, trial_recording_err = self.common._load_trial_recording(event)
        if trial_recording_err or trial_recording is None:
            current_app.logger.error(
                f"Error loading trial recording: {trial_recording_err}"
            )
            return False, trial_recording_err

        # Update metadata and preprocess only the edited footstep
        row = metadata_df.loc[metadata_df["FootstepID"] == new_archive_key].iloc[0]
        footstep_data = trial_recording[
            row["StartFrame"] : row["EndFrame"],
            row["YMin"] : row["YMax"],
            row["XMin"] : row["XMax"],
        ]

        row_mask = metadata_df["FootstepID"] == new_archive_key

        single_metadata = metadata_df.loc[row_mask].copy().reset_index(drop=True)
        processed, updated_metadata = preprocess_footsteps(
            {new_archive_key: footstep_data},
            single_metadata,
            h=100,
            w=100,
        )
        processed_step = processed[0]

        for column in updated_metadata.columns:
            if column == "FootstepID":
                continue
            metadata_df.loc[row_mask, column] = updated_metadata.at[0, column]

        _rewrite_step_archive(
            trial_folder / "steps.npz",
            archive_key_updates=archive_key_updates,
            replacement_arrays={new_archive_key: processed_step},
        )
        _rewrite_step_archive(
            trial_folder / "steps.raw.npz",
            archive_key_updates=archive_key_updates,
            replacement_arrays={new_archive_key: footstep_data},
        )

        # replace metadata.csv for the event to with updated df
        _, update_csv_err = _update_csv(metadata_df, metadata_file_path)
        if update_csv_err:
            return False, update_csv_err

        return (
            {
                "step_archive_key": int(new_archive_key),
                "archive_key_updates": archive_key_updates,
            },
            None,
        )

    def delete_footstep(self, footstep: LocalFootstep, event: SwipeEvent):
        archive_key = _get_archive_key(footstep, footstep.footstep_id)

        # open metadata for the event
        trial_folder = uri_to_path(event.trial_npz_uri).parent
        try:
            metadata_file_path = trial_folder / "metadata.csv"
            metadata_df = load_metadata(metadata_file_path)
        except Exception as e:
            current_app.logger.error(f"Error loading metadata: {e}")
            return False, f"Error loading metadata: {e}"

        # Remove footstep from dataframe
        metadata_df = metadata_df.loc[metadata_df["FootstepID"] != archive_key].copy()
        metadata_df, archive_key_updates = _reassign_footstep_ids_by_start_frame(
            metadata_df
        )

        # Redo anchor identification and path tracing
        p100, p100_err = self.common._load_npz_from_uri(event.trial_p100_npz_uri)
        if p100_err or p100 is None:
            current_app.logger.error(f"Error loading p100 data: {p100_err}")
            return False, p100_err

        if not metadata_df.empty:
            metadata_df["path_order"] = -1  # Any footsteps not on path will be -1
            identify_anchor_footstep(metadata_df)

            metadata_df["heading_angle"] = metadata_df.apply(
                get_heading, args=(p100,), axis=1
            )
            metadata_df["path_order"] = metadata_df.apply(reset_path_order, axis=1)
            trace_path(metadata_df)

            metadata_df["is_anchor"] = metadata_df["path_order"] == 0
            metadata_df["is_on_path"] = metadata_df["path_order"] >= 0

        _rewrite_step_archive(
            trial_folder / "steps.npz",
            archive_key_updates=archive_key_updates,
        )
        _rewrite_step_archive(
            trial_folder / "steps.raw.npz",
            archive_key_updates=archive_key_updates,
        )

        # Replace metadata.csv for the event with the updated df
        _, update_csv_err = _update_csv(metadata_df, metadata_file_path)
        if update_csv_err:
            return False, update_csv_err

        return (
            {
                "archive_key_updates": archive_key_updates,
            },
            None,
        )

    def create_draft_footstep(
        self, event_id: str, new_footstep, frame_padding: int = 20
    ):
        event, event_err = self.common._require_event(event_id)
        if event_err or event is None:
            return None, event_err

        trial_recording, trial_recording_err = self.common._load_trial_recording(event)
        if trial_recording_err or trial_recording is None:
            current_app.logger.error(
                f"Error loading trial recording: {trial_recording_err}"
            )
            return None, trial_recording_err

        x_min, x_max, y_min, y_max = _extract_bbox(new_footstep)

        frame_count, height, width = trial_recording.shape
        if x_min < 0 or y_min < 0 or x_min >= x_max or y_min >= y_max:
            return None, "invalid_bbox"
        if x_max > width or y_max > height:
            return None, "invalid_bbox"

        spatial_slice = trial_recording[:, y_min:y_max, x_min:x_max]
        pressure_over_time = np.any(spatial_slice != 0, axis=(1, 2))
        active_frames = np.flatnonzero(pressure_over_time)

        if active_frames.size == 0:
            return None, "no_pressure_data"

        start_frame = max(0, int(active_frames[0]) - frame_padding)
        end_frame = min(frame_count, int(active_frames[-1]) + frame_padding + 1)

        return (
            {
                "StartFrame": start_frame,
                "EndFrame": end_frame,
                "XMin": x_min,
                "XMax": x_max,
                "YMin": y_min,
                "YMax": y_max,
                "time_recording": trial_recording[
                    start_frame:end_frame,
                    y_min:y_max,
                    x_min:x_max,
                ],
            },
            None,
        )

    def create_footstep(self, event_id: str, new_footstep):
        # validate footstep_id and event_id
        event, event_err = self.common._require_event(event_id)
        if event_err or event is None:
            return False, event_err

        # open metadata for the event
        trial_folder = uri_to_path(event.trial_npz_uri).parent
        try:
            metadata_file_path = trial_folder / "metadata.csv"
            metadata_df = load_metadata(metadata_file_path)
        except Exception as e:
            current_app.logger.error(f"Error loading metadata: {e}")
            return False, f"Error loading metadata: {e}"

        # open p100 for the event
        p100, p100_err = self.common._load_npz_from_uri(event.trial_p100_npz_uri)
        if p100_err or p100 is None:
            current_app.logger.error(f"Error loading p100 data: {p100_err}")
            return False, p100_err

        start_frame, end_frame = _extract_frame_range(new_footstep)
        x_min, x_max, y_min, y_max = _extract_bbox(new_footstep)
        existing_archive_keys = set()
        if "FootstepID" in metadata_df.columns:
            existing_archive_keys = {
                int(footstep_id)
                for footstep_id in metadata_df["FootstepID"].dropna().tolist()
            }

        new_row: dict[str, Any]
        if metadata_df.empty:
            temp_archive_key = 0
            new_row = {column: None for column in metadata_df.columns}
        else:
            footstep_ids = [
                int(footstep_id)
                for footstep_id in metadata_df["FootstepID"].dropna().tolist()
            ]
            temp_archive_key = max(footstep_ids, default=-1) + 1
            new_row = {
                str(key): value for key, value in metadata_df.iloc[-1].to_dict().items()
            }

        new_row["FootstepID"] = temp_archive_key
        new_row["StartFrame"] = start_frame
        new_row["EndFrame"] = end_frame
        new_row["XMin"] = x_min
        new_row["XMax"] = x_max
        new_row["YMin"] = y_min
        new_row["YMax"] = y_max

        if "x" in new_row:
            new_row["x"] = (x_min + x_max) / 2
        if "y" in new_row:
            new_row["y"] = (y_min + y_max) / 2
        if "t" in new_row:
            new_row["t"] = (start_frame + end_frame) / 2
        if "path_order" in new_row:
            new_row["path_order"] = -1
        if "is_anchor" in new_row:
            new_row["is_anchor"] = False
        if "is_on_path" in new_row:
            new_row["is_on_path"] = False

        metadata_df.loc[len(metadata_df)] = new_row
        metadata_df, archive_key_updates = _reassign_footstep_ids_by_start_frame(
            metadata_df
        )
        new_archive_key = archive_key_updates[temp_archive_key]

        # validate footstep bounding box data
        edited_row = metadata_df.loc[metadata_df["FootstepID"] == new_archive_key].iloc[
            0
        ]
        metadata_df["valid"] = metadata_df["valid"].apply(bool)
        if not _is_within_expected_bb_size(
            edited_row
        ) or not _is_within_expect_duration(edited_row):
            metadata_df.loc[metadata_df["FootstepID"] == new_archive_key, "valid"] = (
                False
            )
        else:
            metadata_df.loc[metadata_df["FootstepID"] == new_archive_key, "valid"] = (
                True
            )

        # find path order (anchor identification and path order identification)
        # print("Finding path order...")
        metadata_df["path_order"] = -1  # Any footsteps not on path will be -1
        # print("Identifying anchor footstep...")
        identify_anchor_footstep(metadata_df)

        metadata_df["heading_angle"] = metadata_df.apply(
            get_heading, args=(p100,), axis=1
        )

        metadata_df["path_order"] = metadata_df.apply(reset_path_order, axis=1)

        trace_path(metadata_df)

        metadata_df["is_anchor"] = metadata_df["path_order"] == 0
        metadata_df["is_on_path"] = metadata_df["path_order"] >= 0

        # take new bounding box data from trial recording and update steps.raw.npz and steps.npz

        # print("Opening trial recording...")
        trial_recording, trial_recording_err = self.common._load_trial_recording(event)
        if trial_recording_err or trial_recording is None:
            current_app.logger.error(
                f"Error loading trial recording: {trial_recording_err}"
            )
            return False, trial_recording_err

        row = metadata_df.loc[metadata_df["FootstepID"] == new_archive_key].iloc[0]
        footstep_data = trial_recording[
            row["StartFrame"] : row["EndFrame"],
            row["YMin"] : row["YMax"],
            row["XMin"] : row["XMax"],
        ]

        row_mask = metadata_df["FootstepID"] == new_archive_key
        single_metadata = metadata_df.loc[row_mask].copy().reset_index(drop=True)
        processed, updated_metadata = preprocess_footsteps(
            {new_archive_key: footstep_data},
            single_metadata,
            h=100,
            w=100,
        )
        processed_step = processed[0]

        for column in updated_metadata.columns:
            if column == "FootstepID":
                continue
            metadata_df.loc[row_mask, column] = updated_metadata.at[0, column]

        _rewrite_step_archive(
            trial_folder / "steps.npz",
            archive_key_updates={
                old_key: new_key
                for old_key, new_key in archive_key_updates.items()
                if old_key in existing_archive_keys
            },
            replacement_arrays={new_archive_key: processed_step},
        )
        _rewrite_step_archive(
            trial_folder / "steps.raw.npz",
            archive_key_updates={
                old_key: new_key
                for old_key, new_key in archive_key_updates.items()
                if old_key in existing_archive_keys
            },
            replacement_arrays={new_archive_key: footstep_data},
        )

        # replace metadata.csv for the event to with updated df
        _, update_csv_err = _update_csv(metadata_df, metadata_file_path)
        if update_csv_err:
            return False, update_csv_err

        return (
            {
                "step_archive_key": int(new_archive_key),
                "archive_key_updates": {
                    old_key: new_key
                    for old_key, new_key in archive_key_updates.items()
                    if old_key in existing_archive_keys
                },
            },
            None,
        )


def _extract_bbox(new_footstep) -> tuple[int, int, int, int]:
    x_min = new_footstep["XMin"] if "XMin" in new_footstep else new_footstep["x_min"]
    x_max = new_footstep["XMax"] if "XMax" in new_footstep else new_footstep["x_max"]
    y_min = new_footstep["YMin"] if "YMin" in new_footstep else new_footstep["y_min"]
    y_max = new_footstep["YMax"] if "YMax" in new_footstep else new_footstep["y_max"]

    return (
        int(x_min),
        int(x_max),
        int(y_min),
        int(y_max),
    )


def _extract_frame_range(new_footstep) -> tuple[int, int]:
    start_frame = (
        new_footstep["StartFrame"]
        if "StartFrame" in new_footstep
        else new_footstep["start_frame"]
    )
    end_frame = (
        new_footstep["EndFrame"]
        if "EndFrame" in new_footstep
        else new_footstep["end_frame"]
    )

    return (
        int(start_frame),
        int(end_frame),
    )


def _update_csv(metadata_df, metadata_file_path):
    try:
        metadata_df.to_csv(metadata_file_path, index=False)
        # print(f"Updated metadata.csv: {metadata_file_path}")
    except Exception as e:
        current_app.logger.error(f"Error saving metadata.csv: {e}")
        return False, f"Error saving metadata.csv: {e}"
    return True, None


def _array_to_npy_bytes(array: np.ndarray) -> bytes:
    buffer = BytesIO()
    np.save(buffer, array)
    return buffer.getvalue()


def _get_archive_key(footstep: LocalFootstep, fallback_key: int) -> int:
    return int(getattr(footstep, "step_archive_key", fallback_key))


def _reassign_footstep_ids_by_start_frame(
    metadata_df: Any,
) -> tuple[Any, dict[int, int]]:
    if metadata_df.empty:
        return metadata_df.reset_index(drop=True), {}

    reordered = metadata_df.sort_values("StartFrame", kind="stable").reset_index(
        drop=True
    )
    old_ids = [int(footstep_id) for footstep_id in reordered["FootstepID"].tolist()]
    archive_key_updates = {old_key: new_key for new_key, old_key in enumerate(old_ids)}
    reordered["FootstepID"] = list(range(len(reordered)))
    return reordered, archive_key_updates


def _member_name_from_key(step_key: int) -> str:
    return f"{int(step_key)}.npy"


def _parse_member_key(member_name: str) -> int | None:
    if not member_name.endswith(".npy"):
        return None

    stem = Path(member_name).stem
    if not stem.isdigit():
        return None

    return int(stem)


def _rewrite_step_archive(
    archive_path: Path,
    *,
    archive_key_updates: dict[int, int],
    replacement_arrays: dict[int, np.ndarray] | None = None,
) -> None:
    replacement_arrays = replacement_arrays or {}
    replacement_bytes = {
        int(step_key): _array_to_npy_bytes(array)
        for step_key, array in replacement_arrays.items()
    }

    with NamedTemporaryFile(
        delete=False, suffix=".npz", dir=archive_path.parent
    ) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with ZipFile(tmp_path, "w", compression=ZIP_DEFLATED) as dst:
            written_member_names: set[str] = set()

            if archive_path.exists():
                with ZipFile(archive_path, "r") as src:
                    for info in src.infolist():
                        member_key = _parse_member_key(info.filename)
                        if member_key is None:
                            dst.writestr(info.filename, src.read(info.filename))
                            written_member_names.add(info.filename)
                            continue

                        if member_key not in archive_key_updates:
                            continue

                        next_member_key = int(archive_key_updates[member_key])
                        next_member_name = _member_name_from_key(next_member_key)
                        next_bytes = replacement_bytes.get(
                            next_member_key, src.read(info.filename)
                        )
                        dst.writestr(next_member_name, next_bytes)
                        written_member_names.add(next_member_name)

            for member_key, member_bytes in replacement_bytes.items():
                member_name = _member_name_from_key(member_key)
                if member_name in written_member_names:
                    continue
                dst.writestr(member_name, member_bytes)

        tmp_path.replace(archive_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise
