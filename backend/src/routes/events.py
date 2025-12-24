from flask import Blueprint, jsonify

from backend.src.utils.http import make_error
from backend.src.utils.sal import get_sal

events_bp = Blueprint("events", __name__)


@events_bp.get("/api/events/<event_id>/full")
def api_event_full(event_id: str):
    """Return all data needed for the Swipe Summary view in one request."""
    try:
        sal = get_sal()

        summary = sal.get_event_summary(event_id)
        if not summary:
            return make_error(404, "not_found", "event not found")

        event, availability = summary

        p100 = sal.get_p100(event_id) or []

        grf_data, grf_err = sal.get_grf(event_id)
        if grf_err == "missing_event":
            return make_error(404, "not_found", "event not found")
        grf = grf_data or []

        footsteps, footsteps_err = sal.get_footsteps(event_id)
        if footsteps_err == "missing_event":
            return make_error(404, "not_found", "event not found")
        if footsteps_err == "missing_file":
            footsteps = []

        return jsonify(
            {
                "event": event,
                "availability": availability,
                "p100": p100,
                "grf": grf,
                "footsteps": footsteps,
            }
        )
    except Exception as exc:
        return make_error(500, "internal_error", "unexpected error", str(exc))

@events_bp.get("/api/events/<event_id>/footsteps/p100s")
def api_event_footstep_p100s(event_id: str):
    from backend.src.utils.sal import get_sal

    try:
        items, err = get_sal().get_all_footstep_p100(event_id)
        if err == "missing_event":
            return make_error(404, "not_found", "event not found")
        if err == "missing_file":
            return jsonify({"items": []})
        return jsonify({"items": items})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))
