# backend/src/routes/participants.py
from flask import Blueprint, jsonify

from backend.src.utils.dates import parse_date_str
from backend.src.utils.validation import validate_direction
from backend.src.utils.http import make_error
from backend.src.utils.sal import get_sal

participants_bp = Blueprint("participants", __name__)


@participants_bp.get("/api/participants")
def api_participants():
    try:
        return jsonify({"items": get_sal().get_participants()})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


@participants_bp.get("/api/participants/<int:participant>/dates")
def api_dates(participant: int):
    try:
        items = [d.isoformat() for d in get_sal().get_dates(participant)]
        if not items:
            return make_error(404, "not_found", "no dates for participant")
        return jsonify({"items": items})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


@participants_bp.get("/api/participants/<int:participant>/dates/<date>/directions")
def api_directions(participant: int, date: str):
    dt, err = parse_date_str(date)
    if err:
        return err
    assert dt is not None

    try:
        items = get_sal().get_directions(participant, dt)
        if not items:
            return make_error(404, "not_found", "no directions for participant/date")
        return jsonify({"items": items})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


@participants_bp.get(
    "/api/participants/<int:participant>/dates/<date>/directions/<direction>/events"
)
def api_events(participant: int, date: str, direction: str):
    dt, err = parse_date_str(date)
    if err:
        return err
    assert dt is not None

    derr = validate_direction(direction)
    if derr:
        return derr

    try:
        items = get_sal().get_events(participant, dt, direction)
        if not items:
            return make_error(404, "not_found", "no events for participant/date/direction")
        return jsonify({"items": items})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


@participants_bp.get("/api/participants/<int:participant>/dates/<date>/eventsByDirection")
def api_events_by_direction(participant: int, date: str):
    dt, err = parse_date_str(date)
    if err:
        return err
    assert dt is not None

    try:
        by_dir = get_sal().get_both_direction_events(participant, dt)
        out = {"in": by_dir.get("in", []), "out": by_dir.get("out", [])}
        if not out["in"] and not out["out"]:
            return make_error(404, "not_found", "no events for participant/date")
        return jsonify(out)
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))
