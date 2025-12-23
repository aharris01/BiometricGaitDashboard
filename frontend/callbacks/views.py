# frontend/callbacks/views.py
from dash import Input, Output, callback
from dash.exceptions import PreventUpdate

from frontend.api import API_BASE, fetch_json
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
        footsteps = fetch_json(
            f"{API_BASE}/api/events/{event_id}/footsteps/data",
            context="getFootsteps",
            logger=app.logger,
        )
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

        p100_resp = fetch_json(f"{API_BASE}/api/events/{event_id}/p100", context="getEventP100", logger=app.logger)
        p100 = p100_resp.get("p100", [])

        grf_resp = fetch_json(f"{API_BASE}/api/events/{event_id}/grf", context="getEventGRF", logger=app.logger)
        grf = grf_resp.get("grf", [])

        footsteps = fetch_json(
            f"{API_BASE}/api/events/{event_id}/footsteps/data",
            context="getFootsteps",
            logger=app.logger,
        )

        view = SummaryView(event_id, cmap, p100, grf, footsteps).render()
        return view, footsteps
