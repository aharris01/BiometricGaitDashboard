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
        # Gracefully handle cases where the response is missing or not JSON
        message = None
        details = None
        resp = getattr(exc, "response", None)
        if resp is not None:
            try:
                data = resp.json()
                message = data.get("message")
                details = data.get("details")
            except Exception:
                # Leave message/details as None if the body is not JSON
                pass
        body = {"message": message, "details": details}
        if logger:
            logger.error(
                f"[{context}] Failed to fetch {url}: {body['message']} - {body['details']}"
            )

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


def get_swipe_event_summary_metrics(logger=None):
    return fetch_json(
        f"{API_BASE_URL}/api/events/summaryplot",
        context="get_swipe_event_summary_metrics",
        logger=logger,
    )


# (Optional legacy) not needed anymore after the change, but harmless to keep
def get_event_footstep_p100s(event_id: str, *, logger=None):
    return fetch_json(
        f"{API_BASE_URL}/api/events/{event_id}/footsteps/p100s",
        context="get_event_footstep_p100s",
        logger=logger,
    )
