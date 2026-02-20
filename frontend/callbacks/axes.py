# frontend/callbacks/axes.py

from dash import Input, Output, State, callback, ctx

from frontend.api import get_available_metrics


@callback(
    Output("metrics_x_axis", "options"),
    Output("metrics_y_axis", "options"),
    Output("metrics_axes_store", "data"),
    Input("page-load", "n_intervals"),
    Input("metrics_x_axis", "value"),
    Input("metrics_y_axis", "value"),
    State("metrics_axes_store", "data"),
    prevent_initial_call=False,
)
def manage_axes(_page_load, x_key, y_key, store):
    store = store or {}

    # Load available metrics from backend
    data = get_available_metrics()
    items = data.get("items", [])

    options = [{"label": m.replace("_", " ").title(), "value": m} for m in items]

    # On initial load, no axes selected yet
    if not x_key or not y_key:
        return options, options, {"x": x_key, "y": y_key}

    triggered = ctx.triggered_id

    # Prevent duplicate axis selection
    if x_key == y_key:
        if triggered == "metrics_x_axis":
            y_key = next((m for m in items if m != x_key), None)
        elif triggered == "metrics_y_axis":
            x_key = next((m for m in items if m != y_key), None)

    return options, options, {"x": x_key, "y": y_key}
