# frontend/api.py

import os
import requests
from dash.exceptions import PreventUpdate


# -------------------------------------------------
# API base configuration
# -------------------------------------------------

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


# -------------------------------------------------
# Shared request helper
# -------------------------------------------------


def fetch_json(
    url: str,
    *,
    params: dict | None = None,
    timeout: int = 5,
    context: str = "api_request",
    logger=None,
):
    # Send a GET request and return the decoded JSON body.
    #
    # If the request fails, log the error and raise PreventUpdate
    # so the Dash callback can fail quietly instead of crashing the UI.
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


def post_json(
    url: str,
    *,
    payload: dict,
    timeout: None | int = 5,
    context: str = "api_post",
    logger=None,
):
    # Send a POST request and return the decoded JSON body.
    #
    # If the request fails, log the error and raise PreventUpdate
    # so the Dash callback can fail quietly instead of crashing the UI.
    try:
        if timeout is None:
            resp = requests.post(url, json=payload)
        else:
            resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        message = None
        details = None
        resp = getattr(exc, "response", None)
        if resp is not None:
            try:
                data = resp.json()
                message = data.get("message")
                details = data.get("details")
            except Exception:
                pass

        if logger:
            logger.error(f"[{context}] Failed to post {url}: {message} - {details}")

        raise PreventUpdate


# -------------------------------------------------
# Basic metadata lookups
# -------------------------------------------------


def get_participants(*, logger=None):
    # Return participant dropdown/checklist options.
    data = fetch_json(
        f"{API_BASE_URL}/api/participants",
        context="get_participants",
        logger=logger,
    )
    return [{"label": str(p), "value": p} for p in data["items"]]


def get_dates(participant: int, *, logger=None):
    # Return date dropdown options for one participant.
    data = fetch_json(
        f"{API_BASE_URL}/api/participants/{participant}/dates",
        context="get_dates",
        logger=logger,
    )
    return [{"label": str(d), "value": str(d)} for d in data["items"]]


def get_directions(participant: int, datestr: str, *, logger=None):
    # Return direction dropdown options for one participant/date pair.
    data = fetch_json(
        f"{API_BASE_URL}/api/participants/{participant}/dates/{datestr}/directions",
        context="get_directions",
        logger=logger,
    )
    return [{"label": str(d), "value": d} for d in data["items"]]


def get_events(participant: int, datestr: str, direction: str, *, logger=None):
    # Return event-number dropdown options for one participant/date/direction selection.
    data = fetch_json(
        f"{API_BASE_URL}/api/participants/{participant}/dates/{datestr}/directions/{direction}/events",
        context="get_events",
        logger=logger,
    )
    return [{"label": str(e), "value": e} for e in data["items"]]


# -------------------------------------------------
# Date filter helpers
# -------------------------------------------------


def get_date_part(
    part: str,
    participants: list[int] | None = None,
    year: int | None = None,
    month: int | None = None,
    logger=None,
):
    # Fetch distinct year/month/day values used by the summary page filters.
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


def get_date_bounds(participants: list[int] | None = None, *, logger=None):
    # Fetch the min and max available dates, optionally filtered by participant.
    params = {}
    if participants:
        params["participants"] = ",".join(str(p) for p in participants)

    return fetch_json(
        f"{API_BASE_URL}/api/events/date_bounds",
        params=params,
        context="get_date_bounds",
        logger=logger,
    )


# -------------------------------------------------
# Event detail lookups
# -------------------------------------------------


def get_event_full(event_id: str, *, logger=None):
    # Fetch the combined event detail payload used by the summary view.
    return fetch_json(
        f"{API_BASE_URL}/api/events/{event_id}/full",
        context="get_event_full",
        logger=logger,
    )


def get_event_footstep_p100s(event_id: str, *, logger=None):
    # (Optional legacy) not needed anymore after the change, but harmless to keep
    return fetch_json(
        f"{API_BASE_URL}/api/events/{event_id}/footsteps/p100s",
        context="get_event_footstep_p100s",
        logger=logger,
    )


def get_available_metrics(*, logger=None):
    # Return the list of metrics available for the summary scatter plot.
    return fetch_json(
        f"{API_BASE_URL}/api/events/metrics",
        context="get_available_metrics",
        logger=logger,
    )


# -------------------------------------------------
# Summary view data
# -------------------------------------------------


def get_swipe_event_summary_metrics(
    x_key,
    y_key,
    filters=None,
    logger=None,
):
    # Fetch summary scatter-plot data for the selected x/y metrics
    # and any currently applied summary filters.
    params = {"x": x_key, "y": y_key}

    if filters:
        if "participants" in filters:
            params["participants"] = ",".join(map(str, filters["participants"]))

        # date parts
        if "year" in filters:
            params["year"] = filters["year"]
        if "month" in filters:
            params["month"] = filters["month"]
        if "day" in filters:
            params["day"] = filters["day"]

        # date range
        if "date_from" in filters:
            params["date_from"] = filters["date_from"]
        if "date_to" in filters:
            params["date_to"] = filters["date_to"]

    return fetch_json(
        f"{API_BASE_URL}/api/events/summaryplot",
        params=params,
        context="get_swipe_event_summary_metrics",
        logger=logger,
    )


# -------------------------------------------------
# Footstep page search
# -------------------------------------------------


def search_footsteps(
    event_ids: list[str] | None = None,
    *,
    participants: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    width_min: int | None = None,
    width_max: int | None = None,
    height_min: int | None = None,
    height_max: int | None = None,
    size_min: int | None = None,
    size_max: int | None = None,
    offset: int = 0,
    limit: int = 60,
    logger=None,
):
    # Build the query params for the Footsteps view search route.
    #
    # Only include optional filters when they have values so the request
    # stays small and easy for the backend to interpret.
    params: dict[str, object] = {
        "offset": offset,
        "limit": limit,
    }

    if event_ids:
        params["event_ids"] = ",".join(event_ids)

    if participants:
        params["participants"] = ",".join(str(p) for p in participants)

    if date_from:
        params["date_from"] = date_from

    if date_to:
        params["date_to"] = date_to

    if width_min is not None:
        params["width_min"] = width_min

    if width_max is not None:
        params["width_max"] = width_max

    if height_min is not None:
        params["height_min"] = height_min

    if height_max is not None:
        params["height_max"] = height_max

    if size_min is not None:
        params["size_min"] = size_min

    if size_max is not None:
        params["size_max"] = size_max

    return fetch_json(
        f"{API_BASE_URL}/api/footsteps/search",
        params=params,
        context="search_footsteps",
        logger=logger,
    )


def get_footstep_details(event_id: str, footstep_id: int, *, logger=None):
    # Fetch the per-footstep p100 and GRF payload for the context panel.
    return fetch_json(
        f"{API_BASE_URL}/api/events/{event_id}/footsteps/{footstep_id}",
        context="get_footstep_details",
        logger=logger,
    )


def get_footstep_review(event_id: str, footstep_id: int, *, logger=None):
    # Fetch the full-event review payload for one footstep.
    return fetch_json(
        f"{API_BASE_URL}/api/footsteps/{event_id}/{footstep_id}/review",
        context="get_footstep_review",
        logger=logger,
    )


def save_footstep_review(
    event_id: str,
    footstep_id: int,
    *,
    x_min: int,
    x_max: int,
    y_min: int,
    y_max: int,
    start_frame: int,
    end_frame: int,
    label: str | None,
    logger=None,
):
    # Save one local footstep bbox/label edit and return the refreshed payload.
    return post_json(
        f"{API_BASE_URL}/api/footsteps/{event_id}/{footstep_id}/review",
        payload={
            "x_min": x_min,
            "x_max": x_max,
            "y_min": y_min,
            "y_max": y_max,
            "start_frame": start_frame,
            "end_frame": end_frame,
            "label": label,
        },
        context="save_footstep_review",
        logger=logger,
        timeout=None,
    )


# Create Footstep Helper Function
def create_footstep(
    event_id: str,
    *,
    start_frame: int,
    end_frame: int,
    x_min: int,
    x_max: int,
    y_min: int,
    y_max: int,
    label: str | None,
    logger=None,
):
    # Create one new local footstep and return its review payload.
    return post_json(
        f"{API_BASE_URL}/api/footsteps/{event_id}/create",
        payload={
            "start_frame": start_frame,
            "end_frame": end_frame,
            "x_min": x_min,
            "x_max": x_max,
            "y_min": y_min,
            "y_max": y_max,
            "label": label,
        },
        context="create_footstep",
        logger=logger,
    )


# Delete Function Helper Function
def delete_footstep(
    event_id: str,
    footstep_id: int,
    *,
    logger=None,
):
    # Delete one local footstep.
    return post_json(
        f"{API_BASE_URL}/api/footsteps/{event_id}/{footstep_id}/delete",
        payload={},
        context="delete_footstep",
        logger=logger,
    )
