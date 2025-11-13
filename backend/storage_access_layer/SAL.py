
from .db import DB
from . import validators as v

class SAL:
    #requested seperate SAL file with accessfunctions now living on db.py
    def __init__(self, db=None):
        self.db = db or DB()

    def getParticipants(self):
            result = self.db.getParticipants()
            v.getParticipants_check(result)
            return result

    def getDates(self, participant):
            result = self.db.getDates(participant)
            v.getDates_check(participant, result)
            return result

    def getDirections(self, participant, date):
            result = self.db.getDirections(participant, date)
            v.getDirections_check(participant, date, result)
            return result

    def getEvents(self, participant, date, direction):
            result = self.db.getEvents(participant, date, direction)
            v.getEvents_check(participant, date, direction, result)
            return result

    def getSwipeEventId(self, participant, date, event, direction):
            result = self.db.getSwipeEventId(participant, date, event, direction)
            v.getSwipeEventId_check(participant, date, event, direction, result)
            return result

    def getBothDirectionEvents(self, participant, date):
            result = self.db.getBothDirectionEvents(participant, date)
            v.getBothDirectionEvents_check(participant, date, result)
            return result



