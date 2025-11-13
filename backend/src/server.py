# backend/src/server.py
from __future__ import annotations
import os
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load root .env
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# Config
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "http://127.0.0.1:8050")
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"

# App
server = Flask(__name__)
CORS(server, supports_credentials=True, resources={r"/api/*": {"origins": ALLOWED_ORIGIN}})

# ---- SAL: use the *existing* names, don't break teammates' code ----
from backend.storage_access_layer.accessfunctions import (  # noqa: E402
    getParticipants as sal_getParticipants,
    getDates as sal_getDates,
)

# ---- Direct DB access for event lookups (internal helper) ----
#from backend.storage_access_layer.db import (  # noqa: E402
#    SwipeEvent,
#    get_session,
#)
import backend.storage_access_layer.db as db

def _uri_to_path(uri_or_path: str) -> Path:
    if uri_or_path.startswith("file://"):
        p = urlparse(uri_or_path).path

        # Windows fix
        if os.name == "nt":
            if p.startswith("/") and len(p) > 3 and p[2] == ":":
                p = p[1:]

        return Path(p)

    return Path(uri_or_path)


def _load_swipe(event_id: str) -> db.SwipeEvent | None:
    with db.get_session() as s:
        return s.get(db.SwipeEvent, event_id)


# ------------------------- Health -------------------------
@server.get("/api/health")
def health_check():
    # Keep exactly this payload so the existing unit test passes
    return jsonify({"status": "ok"})


# ------------------- Participants / Dates -----------------
@server.get("/api/participants")
def api_participants():
    return jsonify(sal_getParticipants())


@server.get("/api/participants/<int:participant>/dates")
def api_dates(participant: int):
    # Convert date objects to ISO strings for JSON
    return jsonify([d.isoformat() for d in sal_getDates(participant)])


# --------------- Swipe Event Summary Endpoints ------------
@server.get("/api/events/<event_id>/summary")
def api_event_summary(event_id: str):
    row = _load_swipe(event_id)
    if not row:
        return jsonify({"error": "event not found"}), 404

    p100_exists = _uri_to_path(row.trial_p100_npz_uri).exists()
    grf_exists = _uri_to_path(row.trial_grf_npz_uri).exists()
    trial_exists = _uri_to_path(row.trial_npz_uri).exists()

    event = {
        "id": row.event_id,
        "participant": row.participant,
        "date": row.date.isoformat(),
        "direction": row.direction,
        "event_number": row.event_number,
    }
    availability = {"p100": p100_exists, "grf": grf_exists, "footsteps": trial_exists}
    return jsonify({"event": event, "availability": availability})


@server.get("/api/events/<event_id>/p100")
def api_event_p100(event_id: str):
    row = _load_swipe(event_id)
    if not row:
        return jsonify({"error": "event not found"}), 404

    p = _uri_to_path(row.trial_p100_npz_uri)
    if not p.exists():
        return jsonify({"error": "p100 not available"}), 404

    data = np.load(p)
    # Try common keys; fall back to the first array in the file
    for key in ("p100", "a", "arr_0"):
        if key in data:
            arr = data[key]
            break
    else:
        arr = list(data.values())[0]

    arr = np.rot90(arr, 1)  # rotate 90° for horizontal display
    return jsonify({"p100": arr.tolist()})


@server.get("/api/events/<event_id>/grf")
def api_event_grf(event_id: str):
    row = _load_swipe(event_id)
    if not row:
        return jsonify({"error": "event not found"}), 404

    p = _uri_to_path(row.trial_grf_npz_uri)
    if not p.exists():
        return jsonify({"error": "grf not available"}), 404

    data = np.load(p)
    for key in ("grf", "g", "arr_0"):
        if key in data:
            arr = data[key]
            break
    else:
        arr = list(data.values())[0]

    arr = np.asarray(arr).reshape(-1)
    return jsonify({"grf": arr.tolist()})


@server.get("/api/events/<event_id>/footsteps/data")
def api_event_footsteps(event_id: str):
    row = _load_swipe(event_id)
    if not row:
        return jsonify({"error": "event not found"}), 404

    p = _uri_to_path(row.trial_npz_uri)
    if not p.exists():
        return jsonify([])

    z = np.load(p)
    steps = []
    # Look for keys like footstep_0_p100 / footstep_0_grf
    idx = 0
    while True:
        k_p = f"footstep_{idx}_p100"
        k_g = f"footstep_{idx}_grf"
        if k_p not in z and k_g not in z:
            break
        item = {"footstep_id": idx}
        if k_p in z:
            item["p100"] = np.asarray(z[k_p]).tolist()
        if k_g in z:
            g = np.asarray(z[k_g]).reshape(-1)
            item["grf"] = g.tolist()
        steps.append(item)
        idx += 1

    return jsonify(steps)


def runBackend():
    server.run(host="127.0.0.1", port=8000, debug=False)
