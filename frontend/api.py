# frontend/api.py
import os
import requests
from dash.exceptions import PreventUpdate

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def fetch_json(
    url: str,
    *,
    params: dict | None = None,
    timeout: int = 5,
    context: str = "api_request",
    logger=None,
):
    try:
        resp = requests.get(url, params=params, timeout=timeout)
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


def get_date_part(
    part: str,
    participants: list[int] | None = None,
    year: int | None = None,
    month: int | None = None,
    logger=None,
):
    params = {}

    if participants:
        params["participants"] = ",".join(str(p) for p in participants)

    if year:
        params["year"] = year

    if month:
        params["month"] = month

    if part == "year":
        url = f"{API_BASE_URL}/api/events/years"
    elif part == "month":
        url = f"{API_BASE_URL}/api/events/months"
    elif part == "day":
        url = f"{API_BASE_URL}/api/events/days"
    else:
        return []

    return fetch_json(
        url,
        params=params,
        context=f"get_{part}s",
        logger=logger,
    )


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


def get_swipe_event_summary_metrics(
    x_key,
    y_key,
    filters=None,
    logger=None,
):
    params = {"x": x_key, "y": y_key}

    if filters:
        if "participants" in filters:
            params["participants"] = ",".join(map(str, filters["participants"]))

        if "year" in filters:
            params["year"] = filters["year"]

        if "month" in filters:
            params["month"] = filters["month"]

        if "day" in filters:
            params["day"] = filters["day"]

        if "steps_min" in filters:
            params["steps_min"] = filters["steps_min"]

        if "steps_max" in filters:
            params["steps_max"] = filters["steps_max"]

        if "box_min" in filters:
            params["box_min"] = filters["box_min"]

        if "box_max" in filters:
            params["box_max"] = filters["box_max"]

    return fetch_json(
        f"{API_BASE_URL}/api/events/summaryplot",
        params=params,
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


def get_available_metrics(*, logger=None):
    return fetch_json(
        f"{API_BASE_URL}/api/events/metrics",
        context="get_available_metrics",
        logger=logger,
    )
