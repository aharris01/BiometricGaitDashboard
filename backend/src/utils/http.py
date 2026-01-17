# backend/src/utils/http.py
from typing import Any, Optional, Tuple
from flask import jsonify


def make_error(
    http: int,
    code: str,
    message: str,
    details: Optional[Any] = None,
) -> Tuple[Any, int]:
    """Standard JSON error response used by all endpoints."""
    return jsonify({"code": code, "message": message, "details": details}), http
