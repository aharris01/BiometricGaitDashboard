# backend/storage_access_layer/validators.py
from datetime import date


# ---------- snake_case validators ----------

def get_participants_check(result):
    if not isinstance(result, list):
        raise ValueError("get_participants must return list[int]")
    for p in result:
        if not isinstance(p, int):
            raise ValueError(f"get_participants returned non-int value: {p}")


def get_dates_check(participant, result):
    if not isinstance(participant, int):
        raise ValueError("participant must be int in get_dates")
    if not isinstance(result, list):
        raise ValueError("get_dates must return list[date]")
    for d in result:
        if not isinstance(d, date):
            raise ValueError(f"get_dates returned non-date value: {d}")


def get_directions_check(participant, dt, result):
    if not isinstance(participant, int):
        raise ValueError("participant must be int in get_directions")
    if not isinstance(dt, date):
        raise ValueError("date must be a datetime.date in get_directions")
    if not isinstance(result, list):
        raise ValueError("get_directions must return list[str]")
    for direction in result:
        if direction not in ("in", "out"):
            raise ValueError(f"get_directions returned invalid direction: {direction}")


def get_events_check(participant, dt, direction, result):
    if not isinstance(participant, int):
        raise ValueError("participant must be int in get_events")
    if not isinstance(dt, date):
        raise ValueError("date must be datetime.date in get_events")
    if direction not in ("in", "out"):
        raise ValueError("direction must be 'in' or 'out' in get_events")

    if not isinstance(result, list):
        raise ValueError("get_events must return list[int]")
    for e in result:
        if not isinstance(e, int):
            raise ValueError(f"get_events returned non-int event: {e}")


def get_swipe_event_id_check(participant, dt, event, direction, result):
    if not isinstance(participant, int):
        raise ValueError("participant must be int in get_swipe_event_id")
    if not isinstance(dt, date):
        raise ValueError("date must be datetime.date in get_swipe_event_id")
    if not isinstance(event, int):
        raise ValueError("event must be int in get_swipe_event_id")
    if direction not in ("in", "out"):
        raise ValueError("direction must be 'in' or 'out' in get_swipe_event_id")

    if result is not None and not isinstance(result, str):
        raise ValueError("get_swipe_event_id must return str or None")


def get_both_direction_events_check(participant, dt, result):
    if not isinstance(participant, int):
        raise ValueError("participant must be int in get_both_direction_events")
    if not isinstance(dt, date):
        raise ValueError("date must be datetime.date in get_both_direction_events")

    if not isinstance(result, dict):
        raise ValueError("get_both_direction_events must return dict[str, list[int]]")

    for key, sub in result.items():
        if not isinstance(key, str):
            raise ValueError("get_both_direction_events must return dict[str, list[int]]")
        if not isinstance(sub, list):
            raise ValueError("get_both_direction_events must return nested lists")
        for v_ in sub:
            if not isinstance(v_, int):
                raise ValueError(f"get_both_direction_events returned non-int event: {v_}")


# ---------- camelCase wrappers (keep old code working) ----------

def getParticipants_check(result):
    return get_participants_check(result)

def getDates_check(participant, result):
    return get_dates_check(participant, result)

def getDirections_check(participant, dt, result):
    return get_directions_check(participant, dt, result)

def getEvents_check(participant, dt, direction, result):
    return get_events_check(participant, dt, direction, result)

def getSwipeEventId_check(participant, dt, event, direction, result):
    return get_swipe_event_id_check(participant, dt, event, direction, result)

def getBothDirectionEvents_check(participant, dt, result):
    return get_both_direction_events_check(participant, dt, result)
