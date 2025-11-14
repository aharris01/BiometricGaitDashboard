# validators.py
from datetime import date

# getParticipants()
def getParticipants_check(result):
    if not isinstance(result, list):
        raise ValueError("getParticipants must return list[int]")
    for p in result:
        if not isinstance(p, int):
            raise ValueError(f"getParticipants returned non-int value: {p}")


# getDates(participant)
def getDates_check(participant, result):
    if not isinstance(participant, int):
        raise ValueError("participant must be int in getDates")
    if not isinstance(result, list):
        raise ValueError("getDates must return list[date]")
    for d in result:
        if not isinstance(d, date):
            raise ValueError(f"getDates returned non-date value: {d}")


# getDirections(participant, date)
def getDirections_check(participant, dt, result):
    if not isinstance(participant, int):
        raise ValueError("participant must be int in getDirections")
    if not isinstance(dt, date):
        raise ValueError("date must be a datetime.date in getDirections")
    if not isinstance(result, list):
        raise ValueError("getDirections must return list[str]")
    for direction in result:
        if direction not in ("in", "out"):
            raise ValueError(f"getDirections returned invalid direction: {direction}")


# getEvents(participant, date, direction)
def getEvents_check(participant, dt, direction, result):
    if not isinstance(participant, int):
        raise ValueError("participant must be int in getEvents")
    if not isinstance(dt, date):
        raise ValueError("date must be datetime.date in getEvents")
    if direction not in ("in", "out"):
        raise ValueError("direction must be 'in' or 'out' in getEvents")

    if not isinstance(result, list):
        raise ValueError("getEvents must return list[int]")
    for e in result:
        if not isinstance(e, int):
            raise ValueError(f"getEvents returned non-int event: {e}")

# getSwipeEventId(participant, date, event, direction)
def getSwipeEventId_check(participant, dt, event, direction, result):
    if not isinstance(participant, int):
        raise ValueError("participant must be int in getSwipeEventId")
    if not isinstance(dt, date):
        raise ValueError("date must be datetime.date in getSwipeEventId")
    if not isinstance(event, int):
        raise ValueError("event must be int in getSwipeEventId")
    if direction not in ("in", "out"):
        raise ValueError("direction must be 'in' or 'out' in getSwipeEventId")

    if result is not None and not isinstance(result, str):
        raise ValueError("getSwipeEventId must return str or None")

# getBothDirectionEvents(participant, date)
def getBothDirectionEvents_check(participant, dt, result):
    if not isinstance(participant, int):
        raise ValueError("participant must be int in getBothDirectionEvents")
    if not isinstance(dt, date):
        raise ValueError("date must be datetime.date in getBothDirectionEvents")

    if not isinstance(result, list):
        raise ValueError("getBothDirectionEvents must return list[list[int]]")

    for sub in result:
        if not isinstance(sub, list):
            raise ValueError("getBothDirectionEvents must return nested lists")
        for v in sub:
            if not isinstance(v, int):
                raise ValueError(f"getBothDirectionEvents returned non-int event: {v}")
