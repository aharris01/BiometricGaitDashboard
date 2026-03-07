# backend/src/routes/swipe.py
from flask import Blueprint, jsonify

from backend.src.utils.dates import parse_date_str
from backend.src.utils.validation import validate_direction
from backend.src.utils.http import make_error
from backend.src.utils.sal_provider import get_sal

swipe_bp = Blueprint("swipe", __name__)


@swipe_bp.get("/api/swipe/<int:participant>/<date>/<direction>/<int:event>")
def api_swipe_lookup(participant: int, date: str, direction: str, event: int):
    dt, err = parse_date_str(date)
    if err:
        return err
    assert dt is not None

    derr = validate_direction(direction)
    if derr:
        return derr

    try:
        event_id = get_sal().get_swipe_event_id(participant, dt, event, direction)
        if not event_id:
            return make_error(404, "not_found", "swipe not found")
        return jsonify({"id": event_id})
    except KeyError:
        return make_error(404, "not_found", "swipe not found")
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))
