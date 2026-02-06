# frontend/utils.py
from dash.exceptions import PreventUpdate
from datetime import datetime


def require_values(context, **kwargs):
    missing = [name for name, value in kwargs.items() if value is None]
    if missing:
        print(
            f"[{context}] Missing parameters: {', '.join(missing)}; skipping data fetch."
        )
        raise PreventUpdate


def parse_date_str(s: str) -> bool:
    fmt = "%Y-%m-%d"
    try:
        datetime.strptime(s, fmt)
        return True
    except ValueError:
        return False

def with_select_all(options, label="Select all", value="__all__"):
    return [{"label": label, "value": value}] + (options or [])
