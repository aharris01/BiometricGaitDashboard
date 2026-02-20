# frontend/callbacks/scatter_click.py

from dash import Input, Output, State, callback, no_update
from dash.exceptions import PreventUpdate


@callback(
    Output("metrics-graph-click-data", "children"),
    Output("event-id-store", "data", allow_duplicate=True),
    Input("box-size-scatter-plot", "clickData"),
    State("metrics_confirmed_events_store", "data"),
    prevent_initial_call=True,
)
def on_click_display_event_id(click_data, confirmed_store):
    if not click_data or not click_data.get("points"):
        raise PreventUpdate

    event_id = click_data["points"][0].get("text")
    if not event_id:
        raise PreventUpdate

    confirmed_ids = set((confirmed_store or {}).get("event_ids", []))
    if event_id not in confirmed_ids:
        return click_data, no_update

    return click_data, {"event_id": event_id}
