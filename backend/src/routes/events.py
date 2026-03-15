# backend/src/routes/events.py

from __future__ import annotations

from flask import Blueprint, jsonify, request, Response

from backend.src.utils.http import make_error
from backend.src.utils.sal_provider import get_sal
from backend.src.utils.images import create_image_bytes
from backend.src.utils.dates import parse_date_str

events_bp = Blueprint("events", __name__)


def _parse_participants(raw: str | None) -> list[int]:
    if not raw:
        return []
    out: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out


@events_bp.get("/api/events/<event_id>/full")
def api_event_full(event_id: str):
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

        details, details_err = sal.get_all_footstep_details(event_id)
        if details_err == "missing_event":
            return make_error(404, "not_found", "event not found")
        if details_err == "missing_file":
            details = []

        return jsonify(
            {
                "event": event,
                "availability": availability,
                "p100": p100,
                "grf": grf,
                "footsteps": footsteps,
                "footstep_details": details,
            }
        )
    except Exception:
        import traceback

        traceback.print_exc()
        raise


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
      - size: 'thumb' or 'full' (optional, currently handled by frontend URL only)
      - format: 'png' or 'webp' (optional, currently handled by create_image_bytes)
      - scale: integer scale factor (optional)
    """
    sal = get_sal()
    p100, _grf, err = sal.get_footstep_data(event_id, step_id)

    if err or p100 is None:
        return Response("Footstep not found", status=404, mimetype="text/plain")

    img = create_image_bytes(p100)

    return Response(
        img.data,
        status=200,
        mimetype=img.mimetype,
        headers={"Cache-Control": "private, max-age=300, no-cache"},
    )


@events_bp.get("/api/events/summaryplot")
def api_swipe_event_summary_plot():
    """
    Returns dict:
      {
        "<event_id>": { "<x>": <val>, "<y>": <val> },
        ...
      }

    Filters:
      - participants=1,2,3
      - year, month, day  (discrete date filter)
      - date_from=YYYY-MM-DD, date_to=YYYY-MM-DD  (range filter)

    NOTE: Backend applies whatever is provided.
    Your frontend rule ("last-used date filter wins") should decide
    whether it sends (year/month/day) OR (date_from/date_to).
    Participant filter always ANDs with the chosen date filter.
    """
    try:
        x = request.args.get("x")
        y = request.args.get("y")

        if not x or not y:
            return make_error(
                400, "bad_request", "Both x and y metrics must be provided"
            )

        sal = get_sal()
        available = set(sal.get_available_metrics())

        if x not in available:
            return make_error(
                400, "bad_request", f"Invalid metric requested for x-axis: {x}"
            )

        if y not in available:
            return make_error(
                400, "bad_request", f"Invalid metric requested for y-axis: {y}"
            )

        participants = _parse_participants(request.args.get("participants"))
        year = request.args.get("year", type=int)
        month = request.args.get("month", type=int)
        day = request.args.get("day", type=int)

        date_from_raw = request.args.get("date_from")
        date_to_raw = request.args.get("date_to")

        dt_from = None
        dt_to = None

        if date_from_raw:
            dt_from, err = parse_date_str(date_from_raw)
            if err:
                return err

        if date_to_raw:
            dt_to, err = parse_date_str(date_to_raw)
            if err:
                return err

        if dt_from is not None and dt_to is not None and dt_from > dt_to:
            return make_error(400, "invalid_argument", "date_from must be <= date_to")

        filters = {
            "participants": participants,
            "year": year,
            "month": month,
            "day": day,
            "date_from": dt_from,
            "date_to": dt_to,
        }

        data = sal.get_swipe_event_summary_plot_data(x, y, filters)

        return jsonify(data)

    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


@events_bp.get("/api/events/date_bounds")
def api_swipe_event_date_bounds():
    try:
        participants = _parse_participants(request.args.get("participants"))

        filters = {}
        if participants:
            filters["participants"] = participants

        sal = get_sal()
        result = sal.get_date_bounds(filters or None)

        return jsonify(result)

    except Exception as e:
        return make_error(
            500, "internal_error", "failed to retrieve date bounds", str(e)
        )


@events_bp.get("/api/events/years")
def api_swipe_event_years():
    try:
        participants = _parse_participants(request.args.get("participants"))

        filters = {}
        if participants:
            filters["participants"] = participants

        sal = get_sal()
        years = sal.get_distinct_date_values("year", filters or None)

        return jsonify(years)

    except Exception as e:
        return make_error(
            500, "internal_error", "failed to retrieve distinct years", str(e)
        )


@events_bp.get("/api/events/months")
def api_swipe_event_months():
    try:
        participants = _parse_participants(request.args.get("participants"))
        year = request.args.get("year", type=int)

        filters = {}
        if participants:
            filters["participants"] = participants
        if year:
            filters["year"] = year

        sal = get_sal()
        months = sal.get_distinct_date_values("month", filters or None)

        return jsonify(months)

    except Exception as e:
        return make_error(
            500, "internal_error", "failed to retrieve distinct months", str(e)
        )


@events_bp.get("/api/events/days")
def api_swipe_event_days():
    try:
        participants = _parse_participants(request.args.get("participants"))
        year = request.args.get("year", type=int)
        month = request.args.get("month", type=int)

        filters = {}
        if participants:
            filters["participants"] = participants
        if year:
            filters["year"] = year
        if month:
            filters["month"] = month

        sal = get_sal()
        days = sal.get_distinct_date_values("day", filters or None)

        return jsonify(days)

    except Exception as e:
        return make_error(
            500, "internal_error", "failed to retrieve distinct days", str(e)
        )


@events_bp.get("/api/events/metrics")
def api_available_metrics():
    try:
        sal = get_sal()
        metrics = sorted(sal.get_available_metrics())
        return jsonify({"items": metrics})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))
