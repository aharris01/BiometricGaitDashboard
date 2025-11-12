# backend/src/server.py
from __future__ import annotations
import os, time
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

import jwt
import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# Load the root .env no matter where we run from
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# -------- Config --------
JWT_SECRET = os.getenv("JWT_SECRET", "local-only")
JWT_ISS = os.getenv("JWT_ISS", "engg4000-auth")
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "http://127.0.0.1:8050")
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"

# -------- App --------
server = Flask(__name__)
CORS(server, supports_credentials=True, resources={r"/api/*": {"origins": ALLOWED_ORIGIN}})

# -------- Storage Layer --------
from backend.storage_access_layer.accessfunctions import (
    get_participants as sal_get_participants,
    get_dates as sal_get_dates,
)
from backend.storage_access_layer.db import get_session, SwipeEvent

# -------- Helpers --------
def require_jwt(scope: str | None = None):
    """Enabled only if ENABLE_AUTH=true."""
    def deco(fn):
        if not ENABLE_AUTH:
            return fn
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return jsonify({"error": "missing_bearer"}), 401
            token = auth.split(" ", 1)[1]
            try:
                payload = jwt.decode(
                    token, JWT_SECRET, algorithms=["HS256"],
                    options={"require": ["exp", "iat", "iss"]}
                )
                if payload.get("iss") != JWT_ISS:
                    return jsonify({"error": "bad_issuer"}), 401
                if scope and scope not in payload.get("scope", []):
                    return jsonify({"error": "insufficient_scope"}), 403
                request.user = payload.get("sub")
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "token_expired"}), 401
            except Exception:
                return jsonify({"error": "invalid_token"}), 401
            return fn(*args, **kwargs)
        return wrapper
    return deco

def _from_uri(uri: str) -> Path:
    if uri.startswith("file://"):
        return Path(urlparse(uri).path)
    return Path(uri)

def _load_swipe(event_id: str) -> SwipeEvent | None:
    with get_session() as s:
        return s.get(SwipeEvent, event_id)

def _availability(row: SwipeEvent) -> dict:
    return {
        "p100": _from_uri(row.trial_p100_npz_uri).exists(),
        "grf":  _from_uri(row.trial_grf_npz_uri).exists(),
        "footsteps": _from_uri(row.trial_npz_uri).exists(),
    }

def _to_json_array(arr: np.ndarray) -> list:
    # JSON-serializable lists; make floats if needed
    if np.issubdtype(arr.dtype, np.integer):
        return arr.tolist()
    return arr.astype(float).tolist()

# -------- Basic endpoints --------
@server.get("/api/health")
def health_check():
    return jsonify({"status": "ok", "time": int(time.time())})

@server.get("/api/participants")
@require_jwt("dataset:read")
def api_participants():
    return jsonify(sal_get_participants())

@server.get("/api/participants/<int:participant>/dates")
@require_jwt("dataset:read")
def api_dates(participant: int):
    return jsonify([d.isoformat() for d in sal_get_dates(participant)])

# -------- Swipe Event Summary feature --------
@server.get("/api/events/<event_id>/summary")
@require_jwt("dataset:read")
def api_event_summary(event_id: str):
    row = _load_swipe(event_id)
    if not row:
        return jsonify({"error": "event_not_found", "id": event_id}), 404
    return jsonify({
        "event": {
            "id": row.event_id,
            "participant": row.participant,
            "date": row.date.isoformat(),
            "direction": row.direction,
            "event_number": row.event_number,
        },
        "availability": _availability(row),
    }), 200

@server.get("/api/events/<event_id>/p100")
@require_jwt("dataset:read")
def api_event_p100(event_id: str):
    row = _load_swipe(event_id)
    if not row:
        return jsonify({"error": "event_not_found", "id": event_id}), 404
    p = _from_uri(row.trial_p100_npz_uri)
    if not p.exists():
        return jsonify({"error": "p100_unavailable"}), 404
    try:
        with np.load(p) as z:
            key = next(iter(z.files), None)
            if key is None:
                return jsonify({"error": "empty_npz"}), 500
            arr = np.rot90(z[key], k=1)  # rotate 90° per spec
        return jsonify({"p100": _to_json_array(arr)}), 200
    except Exception as e:
        return jsonify({"error": "p100_load_failed", "detail": str(e)}), 500

@server.get("/api/events/<event_id>/grf")
@require_jwt("dataset:read")
def api_event_grf(event_id: str):
    row = _load_swipe(event_id)
    if not row:
        return jsonify({"error": "event_not_found", "id": event_id}), 404
    p = _from_uri(row.trial_grf_npz_uri)
    if not p.exists():
        return jsonify({"error": "grf_unavailable"}), 404
    try:
        with np.load(p) as z:
            key = next(iter(z.files), None)
            if key is None:
                return jsonify({"error": "empty_npz"}), 500
            arr = np.ravel(z[key])
        return jsonify({"grf": _to_json_array(arr)}), 200
    except Exception as e:
        return jsonify({"error": "grf_load_failed", "detail": str(e)}), 500

@server.get("/api/events/<event_id>/footsteps/data")
@require_jwt("dataset:read")
def api_event_footsteps(event_id: str):
    row = _load_swipe(event_id)
    if not row:
        return jsonify({"error": "event_not_found", "id": event_id}), 404
    trial = _from_uri(row.trial_npz_uri)
    if not trial.exists():
        return jsonify([]), 200
    try:
        steps = []
        with np.load(trial) as z:
            ids = set()
            for k in z.files:
                if k.startswith("footstep_") and ("_p100" in k or "_grf" in k):
                    parts = k.split("_")
                    if len(parts) > 1 and parts[1].isdigit():
                        ids.add(int(parts[1]))
            for i in sorted(ids):
                pk, gk = f"footstep_{i}_p100", f"footstep_{i}_grf"
                p100 = _to_json_array(np.rot90(z[pk], 1)) if pk in z else None
                grf  = _to_json_array(np.ravel(z[gk]))   if gk in z else None
                steps.append({"footstep_id": i, "p100": p100, "grf": grf})
        return jsonify(steps), 200
    except Exception as e:
        return jsonify({"error": "footsteps_load_failed", "detail": str(e)}), 500

# -------- Runner --------
def runBackend():
    # local-only: bind to loopback; change to 0.0.0.0 if you want LAN access
    server.run(host="127.0.0.1", port=int(os.getenv("PORT", "8000")), debug=False)

if __name__ == "__main__":
    runBackend()
