
from .db import DB, get_session
from . import validators as v

class SAL:
    #requested seperate SAL file with accessfunctions now living on db.py
    def __init__(self, db: DB):
        self.db = db

    def getParticipants(self):
        with get_session() as session:
            result = self.db.getParticipants(session)
            v.getParticipants_check(result)
            return result

    def getDates(self, participant):
        with get_session() as session:
            result = self.db.getDates(session, participant)
            v.getDates_check(participant, result)
            return result

    def getDirections(self, participant, date):
        with get_session() as session:
            result = self.db.getDirections(session, participant, date)
            v.getDirections_check(participant, date, result)
            return result

    def getEvents(self, participant, date, direction):
        with get_session() as session:
            result = self.db.getEvents(session, participant, date, direction)
            v.getEvents_check(participant, date, direction, result)
            return result

    def getSwipeEventId(self, participant, date, event, direction):
        with get_session() as session:
            result = self.db.getSwipeEventId(session, participant, date, event, direction)
            v.getSwipeEventId_check(participant, date, event, direction, result)
            return result

    def getBothDirectionEvents(self, participant, date):
        with get_session() as session:
            result = self.db.getBothDirectionEvents(session, participant, date)
            v.getBothDirectionEvents_check(participant, date, result)
            return result



