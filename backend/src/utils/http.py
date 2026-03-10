# backend/src/utils/http.py
from typing import Any, Optional, Tuple
from flask import jsonify, current_app


def make_error(
    http: int,
    code: str,
    message: str,
    details: Optional[Any] = None,
) -> Tuple[Any, int]:
    """Standard JSON error response used by all endpoints."""
    logger = current_app.logger if current_app else None
    if logger:
        logger.error(f"HTTP {http} - {code}: {message} - details: {details}")
    return jsonify({"code": code, "message": message, "details": details}), http
