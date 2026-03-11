# backend/src/routes/footsteps.py

from datetime import date as date_type
from typing import TypedDict, cast

from flask import Blueprint, jsonify, request

from backend.src.utils.http import make_error
from backend.src.utils.sal_provider import get_sal


# -------------------------------------------------
# Footstep search routes
# -------------------------------------------------

footsteps_bp = Blueprint("footsteps", __name__)


# -------------------------------------------------
# Request parsing helpers
# -------------------------------------------------


class ReviewRequestPayload(TypedDict):
    x_min: int
    x_max: int
    y_min: int
    y_max: int
    label: str | None


class CreateFootstepRequestPayload(TypedDict):
    start_frame: int
    end_frame: int
    x_min: int
    x_max: int
    y_min: int
    y_max: int
    label: str | None


class _ReviewPayloadError(ValueError):
    pass


def _parse_event_ids(raw: str | None) -> list[str]:
    # Parse a comma-separated list of event IDs.
    #
    # Empty values are ignored, and duplicates are removed
    # while preserving the original order.
    if not raw:
        return []

    out: list[str] = []
    seen = set()

    for part in raw.split(","):
        event_id = part.strip()
        if not event_id or event_id in seen:
            continue
        seen.add(event_id)
        out.append(event_id)

    return out


def _parse_participants(raw: str | None) -> list[int]:
    # Parse a comma-separated list of participant IDs.
    #
    # Only digit-only values are accepted here.
    # Invalid values are skipped instead of raising an error.
    if not raw:
        return []

    out: list[int] = []
    seen = set()

    for part in raw.split(","):
        part = part.strip()
        if not part.isdigit():
            continue

        value = int(part)
        if value in seen:
            continue

        seen.add(value)
        out.append(value)

    return out


def _parse_iso_date(raw: str | None):
    # Parse one optional YYYY-MM-DD date string.
    #
    # Returns:
    # - (parsed_date, None) on success
    # - (None, None) if no value was provided
    # - (None, error_response) if the format is invalid
    if not raw:
        return None, None

    try:
        return date_type.fromisoformat(raw), None
    except ValueError:
        return None, make_error(
            400,
            "bad_request",
            f"Invalid date format: {raw}. Expected YYYY-MM-DD",
        )


def _coerce_review_int(value: object, key: str) -> int:
    # Parse one required bbox field from the JSON body.
    #
    # Only simple JSON-compatible scalar values are accepted here.
    # This keeps the parser explicit and Pylance-friendly.
    if value is None:
        raise _ReviewPayloadError(f"Missing required field: {key}")

    if not isinstance(value, (int, float, str)):
        raise _ReviewPayloadError(f"Field {key} must be an integer")

    try:
        return int(value)
    except (TypeError, ValueError):
        raise _ReviewPayloadError(f"Field {key} must be an integer")


def _parse_review_payload():
    # Parse and validate the JSON body for a bbox/label save request.
    raw_body = request.get_json(silent=True)

    body: dict[str, object]
    if isinstance(raw_body, dict):
        body = cast(dict[str, object], raw_body)
    else:
        body = {}

    try:
        x_min = _coerce_review_int(body.get("x_min"), "x_min")
        x_max = _coerce_review_int(body.get("x_max"), "x_max")
        y_min = _coerce_review_int(body.get("y_min"), "y_min")
        y_max = _coerce_review_int(body.get("y_max"), "y_max")
    except _ReviewPayloadError as exc:
        return None, make_error(
            400,
            "bad_request",
            str(exc),
        )

    label_raw = body.get("label")
    label: str | None
    if label_raw is None:
        label = None
    else:
        label = str(label_raw).strip() or None

    parsed: ReviewRequestPayload = {
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
        "label": label,
    }

    return parsed, None


def _parse_create_footstep_payload():
    raw_body = request.get_json(silent=True)

    body: dict[str, object]
    if isinstance(raw_body, dict):
        body = cast(dict[str, object], raw_body)
    else:
        body = {}

    try:
        start_frame = _coerce_review_int(body.get("start_frame"), "start_frame")
        end_frame = _coerce_review_int(body.get("end_frame"), "end_frame")
        x_min = _coerce_review_int(body.get("x_min"), "x_min")
        x_max = _coerce_review_int(body.get("x_max"), "x_max")
        y_min = _coerce_review_int(body.get("y_min"), "y_min")
        y_max = _coerce_review_int(body.get("y_max"), "y_max")
    except _ReviewPayloadError as exc:
        return None, make_error(
            400,
            "bad_request",
            str(exc),
        )

    label_raw = body.get("label")
    label: str | None
    if label_raw is None:
        label = None
    else:
        label = str(label_raw).strip() or None

    parsed: CreateFootstepRequestPayload = {
        "start_frame": start_frame,
        "end_frame": end_frame,
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
        "label": label,
    }

    return parsed, None


# -------------------------------------------------
# Footstep search endpoint
# -------------------------------------------------


@footsteps_bp.get("/api/footsteps/search")
def api_search_footsteps():
    # Read query parameters, validate simple ranges, and pass the
    # normalized values to the SAL footstep search path.
    try:
        event_ids = _parse_event_ids(request.args.get("event_ids"))
        participants = _parse_participants(request.args.get("participants"))

        date_from, err = _parse_iso_date(request.args.get("date_from"))
        if err:
            return err

        date_to, err = _parse_iso_date(request.args.get("date_to"))
        if err:
            return err

        # Numeric range filters for footstep dimensions and total area.
        width_min = request.args.get("width_min", type=int)
        width_max = request.args.get("width_max", type=int)
        height_min = request.args.get("height_min", type=int)
        height_max = request.args.get("height_max", type=int)
        size_min = request.args.get("size_min", type=int)
        size_max = request.args.get("size_max", type=int)

        # Pagination inputs.
        offset = request.args.get("offset", default=0, type=int)
        limit = request.args.get("limit", default=60, type=int)

        # Keep pagination values in a safe range.
        if offset is None or offset < 0:
            offset = 0

        if limit is None:
            limit = 60
        limit = max(1, min(limit, 200))

        # Validate date and numeric ranges before calling the SAL.
        if date_from is not None and date_to is not None and date_from > date_to:
            return make_error(
                400,
                "bad_request",
                "date_from must be <= date_to",
            )

        if width_min is not None and width_max is not None and width_min > width_max:
            return make_error(
                400,
                "bad_request",
                "width_min must be <= width_max",
            )

        if (
            height_min is not None
            and height_max is not None
            and height_min > height_max
        ):
            return make_error(
                400,
                "bad_request",
                "height_min must be <= height_max",
            )

        if size_min is not None and size_max is not None and size_min > size_max:
            return make_error(
                400,
                "bad_request",
                "size_min must be <= size_max",
            )

        # Delegate the real search work to the SAL layer.
        result = get_sal().search_footsteps(
            event_ids=event_ids or None,
            participants=participants or None,
            date_from=date_from,
            date_to=date_to,
            width_min=width_min,
            width_max=width_max,
            height_min=height_min,
            height_max=height_max,
            size_min=size_min,
            size_max=size_max,
            offset=offset,
            limit=limit,
        )

        return jsonify(result)

    except Exception as e:
        # Keep unexpected failures in a consistent API error shape.
        return make_error(500, "internal_error", "unexpected error", str(e))


@footsteps_bp.get("/api/footsteps/<event_id>/<int:footstep_id>/review")
def api_get_footstep_review(event_id: str, footstep_id: int):
    # Return the full-event review payload for one footstep.
    try:
        result, err = get_sal().get_footstep_review_context(event_id, footstep_id)

        if err == "missing_event":
            return make_error(404, "not_found", "event not found")

        if err == "missing_file":
            return make_error(404, "not_found", "footstep not found")

        if result is None:
            return make_error(
                500,
                "internal_error",
                "review load returned no payload",
            )

        return jsonify(result)

    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


@footsteps_bp.post("/api/footsteps/<event_id>/<int:footstep_id>/review")
def api_save_footstep_review(event_id: str, footstep_id: int):
    # Save one local bbox/label edit and return the refreshed review payload.
    try:
        parsed, err = _parse_review_payload()
        if err:
            return err

        if parsed is None:
            return make_error(
                500,
                "internal_error",
                "review payload parser returned no data",
            )

        result, err = get_sal().save_footstep_review(
            event_id,
            footstep_id,
            x_min=parsed["x_min"],
            x_max=parsed["x_max"],
            y_min=parsed["y_min"],
            y_max=parsed["y_max"],
            label=parsed["label"],
        )

        if err == "missing_event":
            return make_error(404, "not_found", "event not found")

        if err == "missing_file":
            return make_error(404, "not_found", "footstep not found")

        if err == "invalid_bbox":
            return make_error(
                400,
                "bad_request",
                "bbox must stay inside the full event image and have positive size",
            )

        if result is None:
            return make_error(
                500,
                "internal_error",
                "review save returned no payload",
            )

        return jsonify(result)

    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


@footsteps_bp.post("/api/footsteps/<event_id>/create")
def api_create_footstep(event_id: str):
    try:
        parsed, err = _parse_create_footstep_payload()
        if err:
            return err

        if parsed is None:
            return make_error(
                500,
                "internal_error",
                "create payload parser returned no data",
            )

        result, err = get_sal().create_footstep(
            event_id,
            start_frame=parsed["start_frame"],
            end_frame=parsed["end_frame"],
            x_min=parsed["x_min"],
            x_max=parsed["x_max"],
            y_min=parsed["y_min"],
            y_max=parsed["y_max"],
            label=parsed["label"],
        )

        if err == "missing_event":
            return make_error(404, "not_found", "event not found")

        if err == "missing_file":
            return make_error(404, "not_found", "footstep source data not found")

        if err == "invalid_bbox":
            return make_error(
                400,
                "bad_request",
                "bbox must stay inside the full event image and have positive size",
            )

        if err == "invalid_frame":
            return make_error(
                400,
                "bad_request",
                "start_frame and end_frame must be inside the trial and end_frame must be greater than start_frame",
            )

        if result is None:
            return make_error(
                500,
                "internal_error",
                "create footstep returned no payload",
            )

        return jsonify(result)

    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


@footsteps_bp.post("/api/footsteps/<event_id>/<int:footstep_id>/delete")
def api_delete_footstep(event_id: str, footstep_id: int):
    try:
        result, err = get_sal().delete_footstep(event_id, footstep_id)

        if err == "missing_event":
            return make_error(404, "not_found", "event not found")

        if err == "missing_file":
            return make_error(404, "not_found", "footstep not found")

        if result is None:
            return make_error(
                500,
                "internal_error",
                "delete footstep returned no payload",
            )

        return jsonify(result)

    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))
