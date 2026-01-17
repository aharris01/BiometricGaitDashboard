# backend/src/routes/health.py
from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/api/health")
def health_check():
    # Keep exactly this payload for existing tests
    return jsonify({"status": "ok"})
