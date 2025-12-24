# backend/src/server.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from backend.storage_access_layer.sal import SAL

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "http://127.0.0.1:8050")
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))


def create_app(sal: Any | None = None) -> Flask:
    """
    Create app and ALWAYS attach a SAL instance to app.extensions["sal"].

    If tests pass a FakeSAL, we use it.
    Otherwise we create the real SAL once here.
    """
    app = Flask(__name__)

    CORS(
        app,
        supports_credentials=True,
        resources={r"/api/*": {"origins": ALLOWED_ORIGIN}},
    )

    # ✅ Always set SAL on app
    app.extensions["sal"] = sal if sal is not None else SAL()

    from backend.src.routes.health import health_bp
    from backend.src.routes.participants import participants_bp
    from backend.src.routes.events import events_bp
    from backend.src.routes.swipe import swipe_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(participants_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(swipe_bp)

    return app


# Default app
server = create_app()


def run_backend() -> None:
    server.run(host=API_HOST, port=API_PORT, debug=False)


if __name__ == "__main__":
    run_backend()
