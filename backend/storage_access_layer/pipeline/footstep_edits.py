from typing import Any
import numpy as np

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

    def edit_footstep(self, footstep_id: int, event_id: str, new_footstep_data: dict):
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

        # open p100 for the event
        p100, p100_err = self.common._load_npz_from_uri(event.trial_p100_npz_uri)
        if p100_err or p100 is None:
            current_app.logger.error(f"Error loading p100 data: {p100_err}")
            return False, p100_err

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

        return True, None

    def delete_footstep(self, footstep_id: int, event_id: str):
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

        # Remove footstep from dataframe
        metadata_df = metadata_df.loc[metadata_df["FootstepID"] != footstep_id].copy()

        # Update other footsteps accordingly ie. change footstep IDs
        metadata_df.loc[metadata_df["FootstepID"] > footstep_id, "FootstepID"] -= 1
        metadata_df.reset_index(drop=True, inplace=True)

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

        # Remove footstep from steps.raw.npz and steps.npz, and update remaining footsteps array keys accordingly
        trial_recording, trial_recording_err = self.common._load_npz_from_uri(
            event.trial_npz_uri
        )
        if trial_recording_err or trial_recording is None:
            current_app.logger.error(
                f"Error loading trial recording: {trial_recording_err}"
            )
            return False, trial_recording_err

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

        try:
            if footsteps:
                preprocessed_footsteps, _ = preprocess_footsteps(
                    footsteps, metadata_df, h=100, w=100
                )
                preprocessed_footsteps_dict = {
                    str(i): f for i, f in enumerate(preprocessed_footsteps)
                }
                np.savez_compressed(
                    trial_folder / "steps.npz", **preprocessed_footsteps_dict
                )
            else:
                np.savez_compressed(trial_folder / "steps.npz")
        except Exception as e:
            current_app.logger.error(f"Error saving steps.npz: {e}")
            return False, f"Error saving steps.npz: {e}"

        try:
            np.savez(trial_folder / "steps.raw.npz", allow_pickle=True, **raw_footsteps)
        except Exception as e:
            current_app.logger.error(f"Error saving steps.raw.npz: {e}")
            return False, f"Error saving steps.raw.npz: {e}"

        # Replace metadata.csv for the event with the updated df
        _, update_csv_err = _update_csv(metadata_df, metadata_file_path)
        if update_csv_err:
            return False, update_csv_err

        return True, None

    def create_footstep(self):
        pass


def _update_csv(metadata_df, metadata_file_path):
    try:
        metadata_df.to_csv(metadata_file_path, index=False)
        # print(f"Updated metadata.csv: {metadata_file_path}")
    except Exception as e:
        current_app.logger.error(f"Error saving metadata.csv: {e}")
        return False, f"Error saving metadata.csv: {e}"
    return True, None
