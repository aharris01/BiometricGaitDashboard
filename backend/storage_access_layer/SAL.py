from datetime import date
from typing import Dict, List, Literal, cast
from .db import DB
from . import validators as v
import atexit


class SAL:
    # requested seperate SAL file with accessfunctions now living on db.py
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
