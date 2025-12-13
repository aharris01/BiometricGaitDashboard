# backend/src/server.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from backend.storage_access_layer.SAL import SAL

# ---- Load root .env ----
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# ---- Config ----
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "http://127.0.0.1:8050")

# API host/port from env → part of API base URL configuration
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))

# reserved for future
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"

# ---- SAL (shared dependency) ----
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


# ---- App factory ----
def create_app() -> Flask:
    app = Flask(__name__)

    # CORS for /api/*
    CORS(
        app,
        supports_credentials=True,
        resources={r"/api/*": {"origins": ALLOWED_ORIGIN}},
    )

    # Register blueprints
    from backend.src.routes.health import health_bp
    from backend.src.routes.participants import participants_bp
    from backend.src.routes.events import events_bp
    from backend.src.routes.swipe import swipe_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(participants_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(swipe_bp)

    return app


# This is what Dash / tests will import
server = create_app()


# --------------- dev runner ---------------
def runBackend():
    server.run(host=API_HOST, port=API_PORT, debug=False)


if __name__ == "__main__":
    runBackend()
