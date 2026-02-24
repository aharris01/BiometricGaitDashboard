# frontend/callbacks/views.py
from dash import Input, Output, callback
from dash.exceptions import PreventUpdate

from frontend.api import get_event_full
from frontend.views.metrics_graph import MetricsGraph
from frontend.views.summary_view import SummaryView


def register(app, *, cmap):
    @callback(
        Output("metrics-graph-container", "children"),
        Input("page-load", "n_intervals"),
        prevent_initial_call=False,
    )
    def display_metrics_graph(_n):
        return MetricsGraph({}).render()

    @callback(
        Output("summary-container", "children"),
        Output("footsteps-store", "data"),
        Input("event-id-store", "data"),
        prevent_initial_call=False,
    )
    def load_event_and_render_default(store_data):
        if not store_data or not store_data.get("event_id"):
            raise PreventUpdate

        event_id = store_data["event_id"]
        full = get_event_full(event_id, logger=app.logger)

        p100 = full.get("p100", [])
        grf = full.get("grf", [])
        footsteps = full.get("footsteps", [])
        footstep_details = full.get("footstep_details", [])

        # default: show_all ON, step_index 0
        view = SummaryView(
            event_id,
            cmap,
            p100,
            grf,
            footsteps,
            step_p100s=footstep_details,
            show_all=True,
            step_index=0,
        ).render()

        return view, {
            "event_id": event_id,
            "p100": p100,
            "grf": grf,
            "footsteps": footsteps,
            "footstep_details": footstep_details,
        }
