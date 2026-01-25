# frontend/callbacks/views.py
from dash import Input, Output, callback
from dash.exceptions import PreventUpdate

from frontend.api import get_event_full, get_swipe_event_summary_metrics
from frontend.views.metrics_graph import MetricsGraph
from frontend.views.summary_view import SummaryView


def register(app, *, cmap):
    @callback(
        Output("metrics-graph-container", "children"),
        Input("event-id-store", "data"),
        prevent_initial_call=True,
    )
    def display_metrics_graph(store_data):
        if not store_data:
            raise PreventUpdate

        metrics = get_swipe_event_summary_metrics(logger=app.logger)
        return MetricsGraph(metrics).render()

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
        footstep_details = full.get("footstep_details", [])

        view = SummaryView(
            event_id,
            cmap,
            p100,
            grf,
            footsteps,
            step_p100s=footstep_details,  # thumbnails are here now
        ).render()

        # store everything so selection.py can use it without API calls
        return view, {"footsteps": footsteps, "footstep_details": footstep_details}
