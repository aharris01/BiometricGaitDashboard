# backend/src/routes/footsteps.py

from flask import Blueprint, jsonify, request

from backend.src.utils.http import make_error
from backend.src.utils.sal_provider import get_sal

footsteps_bp = Blueprint("footsteps", __name__)


def _parse_event_ids(raw: str | None) -> list[str]:
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


@footsteps_bp.get("/api/footsteps/search")
def api_search_footsteps():
    try:
        event_ids = _parse_event_ids(request.args.get("event_ids"))
        size_min = request.args.get("size_min", type=int)
        size_max = request.args.get("size_max", type=int)

        offset = request.args.get("offset", default=0, type=int)
        limit = request.args.get("limit", default=60, type=int)

        if offset is None or offset < 0:
            offset = 0

        if limit is None:
            limit = 60
        limit = max(1, min(limit, 200))

        if size_min is not None and size_max is not None and size_min > size_max:
            return make_error(
                400,
                "bad_request",
                "size_min must be <= size_max",
            )

        result = get_sal().search_footsteps(
            event_ids=event_ids or None,
            size_min=size_min,
            size_max=size_max,
            offset=offset,
            limit=limit,
        )

        return jsonify(result)

    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))
