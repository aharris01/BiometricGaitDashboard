# frontend/api.py
import requests
from dash.exceptions import PreventUpdate

API_BASE = "http://127.0.0.1:8000"

def fetch_json(url, *, timeout=5, context="API request", logger=None):
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        if logger:
            logger.error(f"[{context}] Failed to fetch {url}: {exc}")
        raise PreventUpdate

def get_participants(*, logger=None):
    data = fetch_json(f"{API_BASE}/api/participants", context="getParticipants", logger=logger)
    return [{"label": str(p), "value": p} for p in data["items"]]

def get_dates(participant, *, logger=None):
    data = fetch_json(f"{API_BASE}/api/participants/{participant}/dates", context="getDates", logger=logger)
    return [{"label": str(d), "value": str(d)} for d in data["items"]]

def get_directions(participant, datestr, *, logger=None):
    data = fetch_json(
        f"{API_BASE}/api/participants/{participant}/dates/{datestr}/directions",
        context="getDirections",
        logger=logger,
    )
    return [{"label": str(d), "value": d} for d in data["items"]]

def get_events(participant, datestr, direction, *, logger=None):
    data = fetch_json(
        f"{API_BASE}/api/participants/{participant}/dates/{datestr}/directions/{direction}/events",
        context="getEvents",
        logger=logger,
    )
    return [{"label": str(e), "value": e} for e in data["items"]]
