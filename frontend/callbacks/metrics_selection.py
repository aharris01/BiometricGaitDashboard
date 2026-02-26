from copy import deepcopy

from dash import Input, Output, State, callback, ctx
from dash.exceptions import PreventUpdate

from frontend.views.swipe_event_view.metrics_graph import MetricsGraph


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
    if not ctx.triggered:
        raise PreventUpdate

    trigger_prop = ctx.triggered[0]["prop_id"]

    # Box/lasso selection updates
    if trigger_prop.endswith(".selectedData"):
        if selected_data and selected_data.get("points"):
            event_ids = _extract_event_ids_from_points(selected_data["points"])
            return {"event_ids": event_ids}
        return {"event_ids": []}

    # Single-click selection updates
    if trigger_prop.endswith(".clickData"):
        if click_data and click_data.get("points"):
            event_ids = _extract_event_ids_from_points(click_data["points"])
            return {"event_ids": event_ids}
        return {"event_ids": []}

    raise PreventUpdate


@callback(
    Output("metrics_selected_events_store", "data"),
    Output("metrics_scatter_selection_store", "data", allow_duplicate=True),
    Output("box-size-scatter-plot", "selectedData"),
    Input("btn-add-selected", "n_clicks"),  # your ">" button
    State("metrics_scatter_selection_store", "data"),
    State("metrics_selected_events_store", "data"),
    prevent_initial_call=True,
)
def add_selected_events(
    _n,
    selection_store,
    selected_store,
):
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

    # Clear transient graph selection after moving events into draft list.
    return (
        {"event_ids": merged},
        {"event_ids": []},
        None,
    )


@callback(
    Output("box-size-scatter-plot", "figure", allow_duplicate=True),
    Input("metrics_scatter_selection_store", "data"),
    Input("metrics_selected_events_store", "data"),
    Input("event-id-store", "data"),
    State("box-size-scatter-plot", "figure"),
    prevent_initial_call=True,
)
def recolor_scatter_points(
    scatter_selection_store, selected_store, event_store, figure
):
    if not figure or not figure.get("data"):
        raise PreventUpdate

    trace0 = figure["data"][0]
    event_ids = trace0.get("text") or []
    if not event_ids:
        raise PreventUpdate

    pending_event_ids = (scatter_selection_store or {}).get("event_ids", [])
    selected_event_ids = (selected_store or {}).get("event_ids", [])
    active_event_id = (event_store or {}).get("event_id")
    marker_colors = MetricsGraph.build_marker_colors(
        event_ids,
        pending_event_ids=pending_event_ids,
        selected_event_ids=selected_event_ids,
        active_event_id=active_event_id,
    )
    marker_opacities = MetricsGraph.build_marker_opacities(
        event_ids,
        pending_event_ids=pending_event_ids,
        selected_event_ids=selected_event_ids,
        active_event_id=active_event_id,
    )
    selectedpoints = MetricsGraph.build_selectedpoint_indices(
        event_ids,
        pending_event_ids=pending_event_ids,
    )

    fig = deepcopy(figure)
    marker = dict(fig["data"][0].get("marker") or {})
    marker["size"] = marker.get("size", 10)
    marker["color"] = marker_colors
    marker["opacity"] = marker_opacities
    fig["data"][0]["marker"] = marker
    fig["data"][0]["selectedpoints"] = selectedpoints
    return fig
