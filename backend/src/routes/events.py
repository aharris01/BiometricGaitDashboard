# backend/src/routes/events.py
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

        # send ALL step thumbnails + per-step GRF in the same response
        footstep_details, details_err = sal.get_all_footstep_details(event_id)
        if details_err == "missing_event":
            return make_error(404, "not_found", "event not found")
        if details_err == "missing_file":
            footstep_details = []

        return jsonify(
            {
                "event": event,
                "availability": availability,
                "p100": p100,
                "grf": grf,
                "footsteps": footsteps,
                "footstep_details": footstep_details,
            }
        )
    except Exception as exc:
        return make_error(500, "internal_error", "unexpected error", str(exc))


# Keep this endpoint if you want; frontend will no longer need it
@events_bp.get("/api/events/<event_id>/footsteps/p100s")
def api_event_footstep_p100s(event_id: str):
    try:
        items, err = get_sal().get_all_footstep_p100(event_id)
        if err == "missing_event":
            return make_error(404, "not_found", "event not found")
        if err == "missing_file":
            return jsonify({"items": []})
        return jsonify({"items": items})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


# Keep this endpoint if you want; frontend will no longer need it
@events_bp.get("/api/events/<event_id>/footsteps/<int:step_id>")
def api_event_footstep_detail(event_id: str, step_id: int):
    try:
        p100, grf, err = get_sal().get_footstep_data(event_id, step_id)
        if err == "missing_event":
            return make_error(404, "not_found", "event not found")
        if err == "missing_file":
            return make_error(404, "not_found", "footstep data not found")
        return jsonify({"p100": p100 or [], "grf": grf or []})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


@events_bp.get("/api/events/summaryplot")
def api_summary_plot():
    try:
        data = get_sal().get_summary_plot_data()
        if not data:
            return make_error(
                500, "internal_error", "could not generate summary data for plot"
            )
        return jsonify(data)
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))
