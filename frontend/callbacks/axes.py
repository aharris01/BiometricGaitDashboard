# frontend/callbacks/axes.py

from dash import Input, Output, State, callback, ctx
from dash.exceptions import PreventUpdate

from frontend.views.metrics_graph import MetricsGraph


def _filter_options(exclude_value: str | None):
    options = MetricsGraph.AXIS_OPTIONS
    if not exclude_value:
        return options
    return [o for o in options if o["value"] != exclude_value]


def _first_available(exclude_value: str | None):
    filtered = _filter_options(exclude_value)
    return filtered[0]["value"] if filtered else None


@callback(
    Output("metrics_x_axis", "options"),
    Output("metrics_y_axis", "options"),
    Output("metrics_axes_store", "data"),
    Input("metrics_x_axis", "value"),
    Input("metrics_y_axis", "value"),
    State("metrics_axes_store", "data"),
    prevent_initial_call=False,
)
def save_axes(x_key, y_key, store):
    store = store or {}

    x_key = x_key or store.get("x", "avg_box_size")
    y_key = y_key or store.get("y", "footstep_count")

    triggered = ctx.triggered_id

    # If both are the same, auto-fix the opposite axis
    if x_key == y_key:
        if triggered == "metrics_x_axis":
            new_y = _first_available(exclude_value=x_key)
            if not new_y:
                raise PreventUpdate
            y_key = new_y
        elif triggered == "metrics_y_axis":
            new_x = _first_available(exclude_value=y_key)
            if not new_x:
                raise PreventUpdate
            x_key = new_x
        else:
            # initial load safety
            y_key = _first_available(exclude_value=x_key) or y_key

    # Filter dropdown options
    x_options = _filter_options(exclude_value=y_key)
    y_options = _filter_options(exclude_value=x_key)

    return (
        x_options,
        y_options,
        {"x": x_key, "y": y_key},
    )
