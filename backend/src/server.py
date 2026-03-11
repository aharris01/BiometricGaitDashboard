# backend/src/server.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Any
import logging

from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from backend.storage_access_layer.sal import SAL

# ---- Load root .env ----
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# ---- Config ----
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "http://127.0.0.1:8050")
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"  # reserved

# ---- Global SAL (still allowed, but app always stores it too) ----
sal: Optional[Any] = None


def get_sal() -> SAL:
    """Return the module-global SAL instance, creating it on first use."""
    global sal
    if sal is None:
        sal = SAL()
    return sal  # type: ignore[return-value]


def create_app(sal: Any | None = None) -> Flask:
    """Create and configure the Flask app.

    Always attaches a SAL-like instance to app.extensions["sal"] so routes can
    reliably read it via current_app.extensions["sal"].
    """
    app = Flask(__name__)

    CORS(
        app,
        supports_credentials=True,
        resources={r"/api/*": {"origins": ALLOWED_ORIGIN}},
    )

    # Guarantee SAL exists on the app
    sal_instance = sal if sal is not None else get_sal()
    globals()["sal"] = sal_instance  # keep module-global in sync
    app.extensions["sal"] = sal_instance

    from backend.src.routes.health import health_bp
    from backend.src.routes.participants import participants_bp
    from backend.src.routes.events import events_bp
    from backend.src.routes.swipe import swipe_bp
    from backend.src.routes.footsteps import footsteps_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(participants_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(swipe_bp)
    app.register_blueprint(footsteps_bp)

    return app


# Default app used by Dash & imports
server = create_app()


def run_backend(debug_mode: bool = False) -> None:
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    server.run(
        host=API_HOST,
        port=API_PORT,
        debug=debug_mode,
        use_reloader=debug_mode,
    )


if __name__ == "__main__":
    run_backend(True)
