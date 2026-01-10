# backend/src/server.py
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime, date
from typing import Tuple, Optional

from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from backend.storage_access_layer.SAL import SAL

# ---- Load root .env ----
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# ---- Config ----
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "http://127.0.0.1:8050")
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"  # reserved for future

# ---- App ----
server = Flask(__name__)
CORS(
    server,
    supports_credentials=True,
    resources={r"/api/*": {"origins": ALLOWED_ORIGIN}},
)

# ---- SAL ----
sal: Optional[SAL] = None


def get_sal() -> SAL:
    """Return the global SAL instance, creating it on first use.

    Tests are free to monkeypatch backend.src.server.sal before any
    endpoint is called; in that case this simply returns the patched SAL.
    """
    global sal
    if sal is None:
        sal = SAL()
    return sal


# ------------------------- Helpers -------------------------
def make_error(http: int, code: str, message: str, details=None):
    return jsonify({"code": code, "message": message, "details": details}), http


def parse_date_str(s: str) -> Tuple[Optional[date], Optional[Tuple]]:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date(), None
    except ValueError:
        return None, make_error(400, "invalid_argument", "date must be YYYY-MM-DD")


def validate_direction(direction: str) -> Optional[Tuple]:
    if direction not in ("in", "out"):
        return make_error(400, "invalid_argument", "direction must be 'in' or 'out'")
    return None


# ------------------------- Health -------------------------
@server.get("/api/health")
def health_check():
    # Keep exactly this payload for existing tests
    return jsonify({"status": "ok"})


# =========================================================
# Frontend ↔ Backend (dropdown population + swipe id)
# =========================================================


# Get participants → { "items": [participant] }
@server.get("/api/participants")
def api_participants():
    try:
        return jsonify({"items": get_sal().get_participants()})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


# Get dates → { "items": [date] }
@server.get("/api/participants/<int:participant>/dates")
def api_dates(participant: int):
    try:
        items = [d.isoformat() for d in get_sal().get_dates(participant)]
        if not items:
            return make_error(404, "not_found", "no dates for participant")
        return jsonify({"items": items})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


# Get directions → { "items": ["in","out"] }
@server.get("/api/participants/<int:participant>/dates/<date>/directions")
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


# Get events → { "items": [1,2,3,...] }
@server.get(
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
            return make_error(
                404, "not_found", "no events for participant/date/direction"
            )
        return jsonify({"items": items})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


# Get events by direction → { "in": [...], "out": [...] }
@server.get("/api/participants/<int:participant>/dates/<date>/eventsByDirection")
def api_events_by_direction(participant: int, date: str):
    dt, err = parse_date_str(date)
    if err:
        return err
    assert dt is not None
    try:
        s = get_sal()
        by_dir = s.get_both_direction_events(
            participant, dt
        )  # {"in":[...], "out":[...]}

        out = {
            "in": by_dir.get("in", []),
            "out": by_dir.get("out", []),
        }
        if not out["in"] and not out["out"]:
            return make_error(404, "not_found", "no events for participant/date")
        return jsonify(out)
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


# Get swipe → { "id": event_id }
@server.get("/api/swipe/<int:participant>/<date>/<direction>/<int:event>")
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
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


# =====================================================
# Frontend ↔ Backend (swipe event summary + assets)
# =====================================================


@server.get("/api/events/<event_id>/summary")
def api_event_summary(event_id: str):
    try:
        result = get_sal().get_event_summary(event_id)
        if not result:
            return make_error(404, "not_found", "event not found")
        event, availability = result
        return jsonify({"event": event, "availability": availability})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


@server.get("/api/events/<event_id>/p100")
def api_event_p100(event_id: str):
    try:
        data = get_sal().get_p100(event_id)
        # None → treat as "no data" and return empty list
        if data is None:
            return jsonify({"p100": []})
        return jsonify({"p100": data})
    except Exception as e:
        # Any unexpected error → 500
        return make_error(500, "internal_error", "unexpected error", str(e))


@server.get("/api/events/<event_id>/grf")
def api_event_grf(event_id: str):
    try:
        data, err = get_sal().get_grf(event_id)
        if err == "missing_event":
            return make_error(404, "not_found", "event not found")
        if err == "missing_file":
            return make_error(404, "not_found", "grf not available")
        return jsonify({"grf": data})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


@server.get("/api/events/<event_id>/footsteps/data")
def api_event_footsteps(event_id: str):
    try:
        data, err = get_sal().get_footsteps(event_id)
        if err == "missing_event":
            return make_error(404, "not_found", "event not found")
        if err == "missing_file":
            # keep previous behaviour: missing trial → empty list
            return jsonify([])
        return jsonify(data)
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


@server.get("/api/events/<event_id>/footsteps/<int:step_id>")
def api_footstep_detail(event_id: str, step_id: int):
    try:
        p100, grf, err = get_sal().get_footstep_data(event_id, step_id)
        if err == "missing_event":
            return make_error(404, "not_found", "event not found")
        if err == "missing_file":
            return make_error(404, "not_found", "footstep data not available")
        return jsonify({"p100": p100, "grf": grf})
    except Exception as e:
        return make_error(500, "internal_error", "unexpected error", str(e))


# --------------- dev runner ---------------
def run_backend():
    server.run(host="127.0.0.1", port=8000, debug=False)


if __name__ == "__main__":
    run_backend()
