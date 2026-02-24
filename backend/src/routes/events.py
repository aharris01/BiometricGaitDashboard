# backend/src/routes/events.py
from flask import Blueprint, jsonify, request, Response

from backend.src.utils.http import make_error
from backend.src.utils.sal import get_sal
from backend.src.utils.images import create_image_bytes

events_bp = Blueprint("events", __name__)


@events_bp.get("/api/events/<event_id>/full")
def api_event_full(event_id: str):
    """Return summary essentials in one request (main plots + footstep metadata)."""
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
    except Exception:
        import traceback

        traceback.print_exc()
        raise


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


@events_bp.get("/api/events/<event_id>/footsteps/<int:step_id>/image")
def get_footstep_image(event_id: str, step_id: int):
    """
    Returns a rendered heatmap image for a footstep's p100 array.

    Query params:
      - size: 'thumb' or 'full' (default: 'thumb')
      - format: 'png' or 'webp' (default: 'png')
      - scale: integer scale factor for thumb upscaling (optional)
    """

    # --- Fetch footstep data from SAL ---
    # Expecting SAL signature like: get_footstep_data(event_id, step_id) -> (p100, grf, err)
    sal = get_sal()
    p100, _grf, err = sal.get_footstep_data(event_id, step_id)

    if err or p100 is None:
        return Response("Footstep not found", status=404, mimetype="text/plain")

    img = create_image_bytes(p100)

    return Response(
        img.data,
        status=200,
        mimetype=img.mimetype,
        headers={
            # Helps during paging/filtering without "storing images" permanently
            "Cache-Control": "private, max-age=300",
        },
    )


@events_bp.get("/api/events/summaryplot")
def api_swipe_event_summary_plot():
    try:
        x = request.args.get("x")
        y = request.args.get("y")
        participants_raw = request.args.get("participants")

        year = request.args.get("year", type=int)
        month = request.args.get("month", type=int)
        day = request.args.get("day", type=int)
        if not x or not y:
            return make_error(
                400,
                "bad_request",
                "Both x and y metrics must be provided",
            )

        filters = {}

        if participants_raw:
            participants = [
                int(p.strip())
                for p in participants_raw.split(",")
                if p.strip().isdigit()
            ]
            if participants:
                filters["participants"] = participants
        if year:
            filters["year"] = year

        if month:
            filters["month"] = month

        if day:
            filters["day"] = day

        data = get_sal().get_swipe_event_summary_plot_data(
            x=x,
            y=y,
            filters=filters or None,
        )

        return jsonify(data)

    except ValueError as e:
        return make_error(400, "bad_request", str(e))

    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


@events_bp.get("/api/events/years")
def api_swipe_event_years():
    try:
        participants_raw = request.args.get("participants")

        filters = {}

        if participants_raw:
            participants = [
                int(p.strip())
                for p in participants_raw.split(",")
                if p.strip().isdigit()
            ]
            if participants:
                filters["participants"] = participants

        years = get_sal().get_distinct_date_part(
            part="year",
            filters=filters or None,
        )

        return jsonify(years)

    except Exception as e:
        return make_error(
            500,
            "internal_error",
            "failed to retrieve distinct years",
            str(e),
        )


@events_bp.get("/api/events/months")
def api_swipe_event_months():
    try:
        participants_raw = request.args.get("participants")
        year = request.args.get("year", type=int)

        filters = {}

        if participants_raw:
            participants = [
                int(p.strip())
                for p in participants_raw.split(",")
                if p.strip().isdigit()
            ]
            if participants:
                filters["participants"] = participants

        if year:
            filters["year"] = year

        months = get_sal().get_distinct_date_part(
            part="month",
            filters=filters or None,
        )

        return jsonify(months)

    except Exception as e:
        return make_error(
            500,
            "internal_error",
            "failed to retrieve distinct months",
            str(e),
        )


@events_bp.get("/api/events/days")
def api_swipe_event_days():
    try:
        participants_raw = request.args.get("participants")
        year = request.args.get("year", type=int)
        month = request.args.get("month", type=int)

        filters = {}

        if participants_raw:
            participants = [
                int(p.strip())
                for p in participants_raw.split(",")
                if p.strip().isdigit()
            ]
            if participants:
                filters["participants"] = participants

        if year:
            filters["year"] = year

        if month:
            filters["month"] = month

        days = get_sal().get_distinct_date_part(
            part="day",
            filters=filters or None,
        )

        return jsonify(days)

    except Exception as e:
        return make_error(
            500,
            "internal_error",
            "failed to retrieve distinct days",
            str(e),
        )


@events_bp.get("/api/events/metrics")
def api_available_metrics():
    try:
        metrics = get_sal().get_available_metrics()
        return jsonify({"items": metrics})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))
