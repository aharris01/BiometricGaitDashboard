# backend/src/utils/dates.py
from datetime import datetime, date
from typing import Optional, Tuple

from .http import make_error


def parse_date_str(s: str) -> Tuple[Optional[date], Optional[Tuple]]:
    """Parse 'YYYY-MM-DD' into a date or return an error response."""
    try:
        return datetime.strptime(s, "%Y-%m-%d").date(), None
    except ValueError:
        return None, make_error(400, "invalid_argument", "date must be YYYY-MM-DD")
