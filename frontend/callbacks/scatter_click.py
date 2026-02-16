# frontend/callbacks/scatter_click.py

from dash import Input, Output, callback
from dash.exceptions import PreventUpdate


@callback(
    Output("metrics-graph-click-data", "children"),
    Output("event-id-store", "data", allow_duplicate=True),
    Input("box-size-scatter-plot", "clickData"),
    prevent_initial_call=True,
)
def on_click_display_event_id(click_data):
    if not click_data or not click_data.get("points"):
        raise PreventUpdate

    event_id = click_data["points"][0].get("text")
    if not event_id:
        raise PreventUpdate

    return click_data, {"event_id": event_id}
