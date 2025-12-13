# backend/src/utils/validation.py
from typing import Optional, Tuple

from .http import make_error


def validate_direction(direction: str) -> Optional[Tuple]:
    """Validate swipe direction: must be 'in' or 'out'."""
    if direction not in ("in", "out"):
        return make_error(400, "invalid_argument", "direction must be 'in' or 'out'")
    return None
