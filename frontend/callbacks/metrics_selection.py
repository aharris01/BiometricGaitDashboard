from dash import Input, Output, State, callback, ctx
from dash.exceptions import PreventUpdate


def _extract_event_ids_from_points(points):
    event_ids = []
    for p in points or []:
        # You set event_id into Scatter.text in _build_scatter()
        eid = p.get("text")
        if eid:
            event_ids.append(eid)
    # dedupe, preserve order
    seen = set()
    out = []
    for eid in event_ids:
        if eid not in seen:
            seen.add(eid)
            out.append(eid)
    return out


@callback(
    Output("metrics_scatter_selection_store", "data"),
    Input("box-size-scatter-plot", "clickData"),
    Input("box-size-scatter-plot", "selectedData"),
    prevent_initial_call=True,
)
def update_scatter_selection(click_data, selected_data):
    triggered = ctx.triggered_id
    if not triggered:
        raise PreventUpdate

    # Box/lasso selection
    if selected_data and selected_data.get("points"):
        event_ids = _extract_event_ids_from_points(selected_data["points"])
        return {"event_ids": event_ids}

    # Single click
    if click_data and click_data.get("points"):
        event_ids = _extract_event_ids_from_points(click_data["points"])
        return {"event_ids": event_ids}

    raise PreventUpdate


@callback(
    Output("metrics_selected_events_store", "data"),
    Input("btn-add-selected", "n_clicks"),  # your ">" button
    State("metrics_scatter_selection_store", "data"),
    State("metrics_selected_events_store", "data"),
    prevent_initial_call=True,
)
def add_selected_events(_n, selection_store, selected_store):
    selection = (selection_store or {}).get("event_ids", [])
    if not selection:
        raise PreventUpdate

    existing = (selected_store or {}).get("event_ids", [])

    # merge + dedupe (preserve order: existing first, then new)
    seen = set(existing)
    merged = list(existing)
    for eid in selection:
        if eid not in seen:
            seen.add(eid)
            merged.append(eid)

    return {"event_ids": merged}
