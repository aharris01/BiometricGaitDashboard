from sqlalchemy import select
from sqlalchemy import distinct
from sqlalchemy.orm import Session
from .db import SwipeEvent
from .db import get_session

import datetime
#function which retreives participants list from the database
def getParticipants() -> list[int]:
    with get_session() as session:
        query = select(distinct(SwipeEvent.participant)).order_by(SwipeEvent.participant)
        return session.scalars(query).all()

#function which retrieves dates based on input participant
def getDates(participant: int) -> list[datetime.date]:
    with get_session() as session:
        query = select(distinct(SwipeEvent.date)).where(SwipeEvent.participant == participant).order_by(SwipeEvent.date)
        return session.scalars(query).all()

#function which retrieves directions based on participant and date. directions can only be "in" or "out"
def getDirections(participant: int, date: datetime.date) -> list[str]:
    with get_session() as session:
        query = select(distinct(SwipeEvent.direction)).where(SwipeEvent.participant == participant, SwipeEvent.date == date).order_by(SwipeEvent.direction)
        return session.scalars(query).all()

#function which retrieves directions based on participant, date and direction
def getEvents(participant: int, date: datetime.date, direction: str) -> list[int]:
     with get_session() as session:
        query = select(distinct(SwipeEvent.event_number)).where(SwipeEvent.participant == participant, SwipeEvent.date == date, SwipeEvent.direction == direction).order_by(SwipeEvent.event_number)
        return session.scalars(query).all()

#function which retrieves full event ID based on participant, date, direction and event info. This is the location of the csv and npz format metadata
def getSwipeEventId(participant: int,date: datetime.date,event: int,direction: str,) -> str | None:
    with get_session() as session:
        query = select(SwipeEvent.event_id).where(SwipeEvent.participant == participant,SwipeEvent.date == date,SwipeEvent.event_number == event,SwipeEvent.direction == direction)
        return session.scalars(query).first()

#helper function that will return a 2 dimensional list storing the events of all directions included for that date. 

def getBothDirectionEvents(participant: int, date: datetime.date) -> list[list[int]]:
    directions = getDirections(participant, date)
    return [getEvents(participant, date, direction) for direction in directions]
