from sqlalchemy import select
from sqlalchemy import distinct
from sqlalchemy.orm import Session
from .db import SwipeEvent

import datetime
#function which retreives participants list from the database
def getParticipants(session: Session) -> list[int]:
    query = select(distinct(SwipeEvent.participant)).order_by(SwipeEvent.participant)
    return session.scalars(query).all()

#function which retrieves dates based on input participant
def getDates(session: Session, participant: int) -> list[datetime.date]:
    query = select(distinct(SwipeEvent.date)).where(SwipeEvent.participant == participant).order_by(SwipeEvent.date)
    return session.scalars(query).all()

#function which retrieves directions based on participant and date. directions can only be "in" or "out"
def getDirections(session: Session, participant: int, date: datetime.date) -> list[str]:
    query = select(distinct(SwipeEvent.direction)).where(SwipeEvent.participant == participant, SwipeEvent.date == date).order_by(SwipeEvent.direction)
    return session.scalars(query).all()

#function which retrieves directions based on participant, date and direction
def getEvents(session: Session, participant: int, date: datetime.date, direction: str) -> list[int]:
     query = select(distinct(SwipeEvent.event_number)).where(SwipeEvent.participant == participant, SwipeEvent.date == date, SwipeEvent.direction == direction).order_by(SwipeEvent.event_number)
     return session.scalars(query).all()

#function which retrieves full event ID based on participant, date, direction and event info. This is the location of the csv and npz format metadata
def getSwipeEventId(session: Session,participant: int,date: datetime.date,event: int,direction: str,) -> str | None:
    query = select(SwipeEvent.event_id).where(SwipeEvent.participant == participant,SwipeEvent.date == date,SwipeEvent.event_number == event,SwipeEvent.direction == direction)
    return session.scalars(query).first()

