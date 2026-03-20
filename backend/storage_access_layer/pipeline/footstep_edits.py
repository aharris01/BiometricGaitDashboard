from io import BytesIO
import os
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
            metadata_df["FootstepID"] == footstep_id,
            ["XMin", "XMax", "YMin", "YMax", "StartFrame", "EndFrame"],
        ] = [
            new_footstep_data["XMin"],
            new_footstep_data["XMax"],
            new_footstep_data["YMin"],
            new_footstep_data["YMax"],
            new_footstep_data["StartFrame"],
            new_footstep_data["EndFrame"],
        ]

        # validate footstep bounding box data
        edited_row = metadata_df.loc[metadata_df["FootstepID"] == footstep_id].iloc[0]
        metadata_df["valid"] = metadata_df["valid"].apply(bool)
        if not _is_within_expected_bb_size(
            edited_row
        ) or not _is_within_expect_duration(edited_row):
            metadata_df.loc[metadata_df["FootstepID"] == footstep_id, "valid"] = False
        else:
            metadata_df.loc[metadata_df["FootstepID"] == footstep_id, "valid"] = True

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
        trial_recording, trial_recording_err = self.common._load_npz_from_uri(
            event.trial_npz_uri
        )
        if trial_recording_err or trial_recording is None:
            current_app.logger.error(
                f"Error loading trial recording: {trial_recording_err}"
            )
            return False, trial_recording_err

        # Update metadata and preprocess only the edited footstep
        row = metadata_df.loc[metadata_df["FootstepID"] == footstep_id].iloc[0]
        footstep_data = trial_recording[
            row["StartFrame"] : row["EndFrame"],
            row["YMin"] : row["YMax"],
            row["XMin"] : row["XMax"],
        ]

        row_mask = metadata_df["FootstepID"] == footstep_id

        single_metadata = metadata_df.loc[row_mask].copy().reset_index(drop=True)
        processed, updated_metadata = preprocess_footsteps(
            {footstep_id: footstep_data},
            single_metadata,
            h=100,
            w=100,
        )

        for column in updated_metadata.columns:
            metadata_df.loc[row_mask, column] = updated_metadata.at[0, column]

        processed_member = f"{footstep_id}.npy"
        raw_member = f"{footstep_id}.npy"

        _rewrite_npz_member(trial_folder / "steps.npz", processed_member, processed)
        _rewrite_npz_member(trial_folder / "steps.raw.npz", raw_member, footstep_data)

        # replace metadata.csv for the event to with updated df
        _, update_csv_err = _update_csv(metadata_df, metadata_file_path)
        if update_csv_err:
            return False, update_csv_err

        return True, None

    def delete_footstep(self, footstep: LocalFootstep, event: SwipeEvent):
        footstep_id = footstep.footstep_id

        # open metadata for the event
        trial_folder = uri_to_path(event.trial_npz_uri).parent
        try:
            metadata_file_path = trial_folder / "metadata.csv"
            metadata_df = load_metadata(metadata_file_path)
        except Exception as e:
            current_app.logger.error(f"Error loading metadata: {e}")
            return False, f"Error loading metadata: {e}"

        # Remove footstep from dataframe
        metadata_df = metadata_df.loc[metadata_df["FootstepID"] != footstep_id].copy()

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

        # Remove footstep from steps.raw.npz and steps.npz by treating archives as zipfiles
        paths = [
            (trial_folder / "steps.npz", trial_folder / "temp.npz"),
            (trial_folder / "steps.raw.npz", trial_folder / "temp.raw.npz"),
        ]
        for src_path, tmp_path in paths:
            with (
                ZipFile(src_path, "r") as src,
                ZipFile(tmp_path, "w", compression=ZIP_DEFLATED) as dst,
            ):
                for info in src.infolist():
                    if info.filename == f"{footstep_id}.npy":
                        continue
                    data = src.read(info.filename)
                    dst.writestr(info.filename, data)
            os.replace(tmp_path, src_path)

        # Replace metadata.csv for the event with the updated df
        _, update_csv_err = _update_csv(metadata_df, metadata_file_path)
        if update_csv_err:
            return False, update_csv_err

        return True, None

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

        start_frame = int(new_footstep.get("StartFrame", new_footstep["start_frame"]))
        end_frame = int(new_footstep.get("EndFrame", new_footstep["end_frame"]))
        x_min = int(new_footstep.get("XMin", new_footstep["x_min"]))
        x_max = int(new_footstep.get("XMax", new_footstep["x_max"]))
        y_min = int(new_footstep.get("YMin", new_footstep["y_min"]))
        y_max = int(new_footstep.get("YMax", new_footstep["y_max"]))

        new_row: dict[str, Any]
        if metadata_df.empty:
            new_footstep_id = 0
            new_row = {column: None for column in metadata_df.columns}
        else:
            start_frames = metadata_df["StartFrame"].to_numpy()
            end_frames = metadata_df["EndFrame"].to_numpy()
            insert_before = (start_frames > start_frame) | (
                (start_frames == start_frame) & (end_frames > end_frame)
            )

            insert_idx = (
                int(insert_before.argmax()) if insert_before.any() else len(metadata_df)
            )
            new_footstep_id = insert_idx

            template_idx = min(insert_idx, len(metadata_df) - 1)
            new_row = {
                str(key): value
                for key, value in metadata_df.iloc[template_idx].to_dict().items()
            }

            metadata_df.loc[
                metadata_df["FootstepID"] >= new_footstep_id, "FootstepID"
            ] += 1

        new_row["FootstepID"] = new_footstep_id
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
        metadata_df = metadata_df.sort_values("FootstepID", kind="stable").reset_index(
            drop=True
        )

        # validate footstep bounding box data
        edited_row = metadata_df.loc[metadata_df["FootstepID"] == new_footstep_id].iloc[
            0
        ]
        metadata_df["valid"] = metadata_df["valid"].apply(bool)
        if not _is_within_expected_bb_size(
            edited_row
        ) or not _is_within_expect_duration(edited_row):
            metadata_df.loc[metadata_df["FootstepID"] == new_footstep_id, "valid"] = (
                False
            )
        else:
            metadata_df.loc[metadata_df["FootstepID"] == new_footstep_id, "valid"] = (
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
        trial_recording, trial_recording_err = self.common._load_npz_from_uri(
            event.trial_npz_uri
        )
        if trial_recording_err or trial_recording is None:
            current_app.logger.error(
                f"Error loading trial recording: {trial_recording_err}"
            )
            return False, trial_recording_err
        # print("Opened trial recording")
        # print("Updating footstep data files...")

        footsteps: dict[Any, np.ndarray] = {}
        raw_footsteps: dict[str, np.ndarray] = {}
        for i, row in metadata_df.iterrows():
            footstep_data = trial_recording[
                row["StartFrame"] : row["EndFrame"],
                row["YMin"] : row["YMax"],
                row["XMin"] : row["XMax"],
            ]
            footsteps[i] = footstep_data
            raw_footsteps[str(i)] = footstep_data

        # print("Normalizing and updating steps.npz...")
        preprocessed_footsteps, _ = preprocess_footsteps(
            footsteps, metadata_df, h=100, w=100
        )
        preprocessed_footsteps_dict = {
            str(i): f for i, f in enumerate(preprocessed_footsteps)
        }
        try:
            np.savez_compressed(
                trial_folder / "steps.npz", **preprocessed_footsteps_dict
            )
            # print(f"Updated steps.npz: {trial_folder / 'steps.npz'}")
        except Exception as e:
            current_app.logger.error(f"Error saving steps.npz: {e}")
            return False, f"Error saving steps.npz: {e}"

        # print("Updating steps.raw.npz...")
        try:
            np.savez(trial_folder / "steps.raw.npz", allow_pickle=True, **raw_footsteps)
            # print(f"Updated steps.raw.npz: {trial_folder / 'steps.raw.npz'}")
        except Exception as e:
            current_app.logger.error(f"Error saving steps.raw.npz: {e}")
            return False, f"Error saving steps.raw.npz: {e}"

        # replace metadata.csv for the event to with updated df
        _, update_csv_err = _update_csv(metadata_df, metadata_file_path)
        if update_csv_err:
            return False, update_csv_err

        return new_footstep_id, None


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


def _rewrite_npz_member(
    archive_path: Path,
    member_name: str,
    new_array: np.ndarray,
) -> None:
    new_bytes = _array_to_npy_bytes(new_array)

    with NamedTemporaryFile(
        delete=False, suffix=".npz", dir=archive_path.parent
    ) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with (
            ZipFile(archive_path, "r") as src,
            ZipFile(tmp_path, "w", compression=ZIP_DEFLATED) as dst,
        ):
            replaced = False

            for info in src.infolist():
                if info.filename == member_name:
                    dst.writestr(member_name, new_bytes)
                    replaced = True
                    continue

                dst.writestr(info.filename, src.read(info.filename))

            if not replaced:
                dst.writestr(member_name, new_bytes)

        tmp_path.replace(archive_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise
