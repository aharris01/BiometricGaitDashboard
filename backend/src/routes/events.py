from flask import Blueprint, jsonify

from backend.src.utils.http import make_error

events_bp = Blueprint("events", __name__)


@events_bp.get("/api/events/<event_id>/summary")
def api_event_summary(event_id: str):
    from backend.src.server import get_sal
    try:
        result = get_sal().getEventSummary(event_id)
        if not result:
            return make_error(404, "not_found", "event not found")
        event, availability = result
        return jsonify({"event": event, "availability": availability})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


@events_bp.get("/api/events/<event_id>/p100")
def api_event_p100(event_id: str):
    from backend.src.server import get_sal
    try:
        data = get_sal().getP100(event_id)
        if data is None:
            return jsonify({"p100": []})
        return jsonify({"p100": data})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


@events_bp.get("/api/events/<event_id>/grf")
def api_event_grf(event_id: str):
    from backend.src.server import get_sal
    try:
        data, err = get_sal().getGRF(event_id)
        if err == "missing_event":
            return make_error(404, "not_found", "event not found")
        if err == "missing_file":
            return make_error(404, "not_found", "grf not available")
        return jsonify({"grf": data})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


@events_bp.get("/api/events/<event_id>/footsteps/data")
def api_event_footsteps(event_id: str):
    from backend.src.server import get_sal
    try:
        data, err = get_sal().getFootsteps(event_id)
        if err == "missing_event":
            return make_error(404, "not_found", "event not found")
        if err == "missing_file":
            return jsonify([])
        return jsonify(data)
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


@events_bp.get("/api/events/<event_id>/footsteps/<int:step_id>")
def api_footstep_detail(event_id: str, step_id: int):
    from backend.src.server import get_sal
    try:
        p100, grf, err = get_sal().getFootstepData(event_id, step_id)
        if err == "missing_event":
            return make_error(404, "not_found", "event not found")
        if err == "missing_file":
            return make_error(404, "not_found", "footstep data not available")
        return jsonify({"p100": p100, "grf": grf})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))
