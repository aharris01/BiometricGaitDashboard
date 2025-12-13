# backend/src/server.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Any

from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from backend.storage_access_layer.SAL import SAL

# ---- Load root .env ----
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# ---- Config ----
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "http://127.0.0.1:8050")
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"  # reserved

# ---- Global SAL, same idea as original code ----
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


def create_app(sal: Any | None = None) -> Flask:
    """Create and configure the Flask app.

    If a SAL-like instance is passed in (e.g. FakeSAL in tests), use it.
    Otherwise, SAL will be created lazily via backend.src.server.get_sal().
    """
    app = Flask(__name__)

    CORS(
        app,
        supports_credentials=True,
        resources={r"/api/*": {"origins": ALLOWED_ORIGIN}},
    )

    if sal is not None:
        # store on the module-global and as an app extension
        globals()["sal"] = sal  # type: ignore[assignment]
        app.extensions["sal"] = sal

    from backend.src.routes.health import health_bp
    from backend.src.routes.participants import participants_bp
    from backend.src.routes.events import events_bp
    from backend.src.routes.swipe import swipe_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(participants_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(swipe_bp)

    return app


# Default app used by Dash & tests that import `server`
server = create_app()


def runBackend() -> None:
    server.run(host=API_HOST, port=API_PORT, debug=False)


if __name__ == "__main__":
    runBackend()
