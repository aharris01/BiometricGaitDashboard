from ..db.db import DB
from ..helpers.common import CommonHelper
from .utils.pipeline_utils import load_metadata

T_MIN = 50
T_MAX = 400

SHORT_DIMENSTION_MIN = 15
SHORT_DIMENSTION_MAX = 80
LONG_DIMENSION_MIN = 40
LONG_DIMENSION_MAX = 100


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
            return None, event_err

        footstep, footstep_err = self.common._require_footstep(event_id, footstep_id)
        if footstep_err or footstep is None:
            return None, footstep_err

        # open metadata for the event
        metadata_file_path = event.trial_npz_uri.replace("steps.npz", "metadata.csv")
        metadata_df = load_metadata(metadata_file_path)

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
        edited_row = metadata_df[metadata_df["FootstepID"] == footstep_id].iloc[0]
        if not _is_within_expected_bb_size(edited_row) or _is_within_expect_duration(
            edited_row
        ):
            metadata_df.loc[metadata_df["FootstepID"] == footstep_id, "valid"] = False

        metadata_df["valid"] = metadata_df["valid"].apply(bool)

        # find path order (anchor identification and path order identification)
        # take new bounding box data from trial recording and update steps.raw.npz and steps.npz
        # replace metadata.csv for the event to with updated df
        # make entry in footsteps table
        # update metrics for event
        # return success or failure
        pass


def _is_within_expected_bb_size(row):
    x_length = row.XMax - row.XMin
    y_length = row.YMax - row.YMin

    short_length = min(x_length, y_length)
    long_length = max(x_length, y_length)

    return (SHORT_DIMENSTION_MIN < short_length < SHORT_DIMENSTION_MAX) and (
        LONG_DIMENSION_MIN < long_length < LONG_DIMENSION_MAX
    )


def _is_within_expect_duration(row):
    duration = row.EndFrame - row.StartFrame
    return T_MIN < duration < T_MAX
