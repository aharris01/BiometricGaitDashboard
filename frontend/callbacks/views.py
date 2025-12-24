# frontend/callbacks/views.py
from dash import Input, Output, callback
from dash.exceptions import PreventUpdate

from frontend.api import get_event_full, get_event_footstep_p100s
from frontend.views.metrics_graph import MetricsGraph
from frontend.views.summary_view import SummaryView


def register(app, *, cmap):
    @callback(
        Output("metrics-graph-container", "children"),
        Input("event-id-store", "data"),
        prevent_initial_call=True,
    )
    def display_metrics_graph(store_data):
        if not store_data or not store_data.get("event_id"):
            raise PreventUpdate

        event_id = store_data["event_id"]
        full = get_event_full(event_id, logger=app.logger)
        footsteps = full.get("footsteps", [])
        return MetricsGraph(event_id, footsteps).render()

    @callback(
        Output("summary-container", "children"),
        Output("footsteps-store", "data"),
        Input("event-id-store", "data"),
        prevent_initial_call=True,
    )
    def display_summary_graph(store_data):
        if not store_data or not store_data.get("event_id"):
            raise PreventUpdate

        event_id = store_data["event_id"]

        full = get_event_full(event_id, logger=app.logger)
        p100 = full.get("p100", [])
        grf = full.get("grf", [])
        footsteps = full.get("footsteps", [])

        steps_resp = get_event_footstep_p100s(event_id, logger=app.logger)
        step_p100s = steps_resp.get("items", [])

        view = SummaryView(
            event_id,
            cmap,
            p100,
            grf,
            footsteps,
            step_p100s=step_p100s,
        ).render()

        return view, footsteps
