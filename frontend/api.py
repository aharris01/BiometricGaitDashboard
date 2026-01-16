# frontend/api.py
import os
import requests
from dash.exceptions import PreventUpdate

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def fetch_json(
    url: str, *, timeout: int = 5, context: str = "api_request", logger=None
):
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        if logger:
            logger.error(f"[{context}] Failed to fetch {url}: {exc}")
        raise PreventUpdate


def get_participants(*, logger=None):
    data = fetch_json(
        f"{API_BASE_URL}/api/participants",
        context="get_participants",
        logger=logger,
    )
    return [{"label": str(p), "value": p} for p in data["items"]]


def get_dates(participant: int, *, logger=None):
    data = fetch_json(
        f"{API_BASE_URL}/api/participants/{participant}/dates",
        context="get_dates",
        logger=logger,
    )
    return [{"label": str(d), "value": str(d)} for d in data["items"]]


def get_directions(participant: int, datestr: str, *, logger=None):
    data = fetch_json(
        f"{API_BASE_URL}/api/participants/{participant}/dates/{datestr}/directions",
        context="get_directions",
        logger=logger,
    )
    return [{"label": str(d), "value": d} for d in data["items"]]


def get_events(participant: int, datestr: str, direction: str, *, logger=None):
    data = fetch_json(
        f"{API_BASE_URL}/api/participants/{participant}/dates/{datestr}/directions/{direction}/events",
        context="get_events",
        logger=logger,
    )
    return [{"label": str(e), "value": e} for e in data["items"]]


def get_event_full(event_id: str, *, logger=None):
    return fetch_json(
        f"{API_BASE_URL}/api/events/{event_id}/full",
        context="get_event_full",
        logger=logger,
    )


# (Optional legacy) not needed anymore after the change, but harmless to keep
def get_event_footstep_p100s(event_id: str, *, logger=None):
    return fetch_json(
        f"{API_BASE_URL}/api/events/{event_id}/footsteps/p100s",
        context="get_event_footstep_p100s",
        logger=logger,
    )
