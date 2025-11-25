from datetime import date
from typing import Dict, List, Literal, cast

import numpy as np
from .db import DB
from . import validators as v
import atexit


class SAL:
    # =========================================================
    # Backend ↔ SAL to get path with event_id Primary key
    # =========================================================

    def __init__(self, db=None):
        self.db = db or DB()
        atexit.register(self._close_db)

    def _close_db(self):
        if getattr(self, "db", None):
            close = getattr(self.db, "close", None)
            if close:
                close()

    def getParticipants(self) -> List[int]:
        raw = self.db.getParticipants()
        result = cast(List[int], raw)
        v.getParticipants_check(result)
        return result

    def getDates(self, participant) -> List[date]:
        raw = self.db.getDates(participant)
        result = cast(List[date], raw)
        v.getDates_check(participant, result)
        return result

    def getDirections(self, participant, date) -> List[Literal["in", "out"]]:
        raw = self.db.getDirections(participant, date)
        result = cast(List[Literal["in", "out"]], raw)
        v.getDirections_check(participant, date, result)
        return result

    def getEvents(self, participant, date, direction) -> List[int]:
        raw = self.db.getEvents(participant, date, direction)
        result = list(raw)
        v.getEvents_check(participant, date, direction, result)
        return result

    def getSwipeEventId(self, participant, date, event, direction) -> str:
        raw = self.db.getSwipeEventId(participant, date, event, direction)
        result = str(raw)
        v.getSwipeEventId_check(participant, date, event, direction, result)
        return result

    def getBothDirectionEvents(self, participant, date) -> Dict[str, List[int]]:
        result = {}
        directions = self.db.getDirections(participant, date)
        for d in directions:
            result[d] = self.db.getEvents(participant, date, d)
        v.getBothDirectionEvents_check(participant, date, result)
        return result

    def getEventSummary(self, event_id: str):
        raise NotImplementedError

    def getP100(self, event_id):
        event = self.db.getSwipeEvent(event_id)

        if event is None:
            return None

        file = event.trial_p100_npz_uri
        # loaded_file = np.load(file)
        # Here, file has the form "file:///D:/../BiometricGaitDashboard/data/<ptcp>/<date>/<direction>/<eid>/trial.p100.npz"
        # file_location truncates the "file:///" since numpy.load reads that as invalid for some reason
        file_location = str(file)[8:]
        loaded_file = np.load(file_location)
        array = loaded_file["arr_0"]
        # see https://stackoverflow.com/questions/26646362/numpy-array-is-not-json-serializable
        pre_json_array = array.tolist()
        # print(len(json_array),'x',len(json_array[0]))
        return pre_json_array

    def getGRF(self, event_id):
        raise NotImplementedError

    def getFootsteps(self, event_id):
        raise NotImplementedError
