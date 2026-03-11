from ..db.db import DB
from ..helpers.common import CommonHelper


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

        # validate footstep bounding box data

        # open metadata for the event
        # load into df
        # make edits to footstep in df
        # find path order (anchor identification and path order identification)
        # take new bounding box data from trial recording and update steps.raw.npz and steps.npz
        # replace metadata.csv for the event to with updated df
        # make entry in footsteps table
        # update metrics for event
        # return success or failure
        pass
