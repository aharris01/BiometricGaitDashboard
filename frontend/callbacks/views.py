# frontend/callbacks/views.py
from dash import Input, Output, callback
from dash.exceptions import PreventUpdate

from frontend.api import get_event_full
from frontend.views.swipe_event_view.metrics_graph import MetricsGraph
from frontend.views.swipe_event_view.summary_view import SummaryView


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
        Input("metrics_confirmed_events_store", "data"),
        prevent_initial_call=False,
    )
    def display_summary_graph(store_data: dict, confirmed_store: dict):
        if not store_data:
            raise PreventUpdate
        elif not isinstance(store_data, str) and not store_data.get("event_id"):
            raise PreventUpdate

        event_id = store_data["event_id"]
        confirmed_ids = set((confirmed_store or {}).get("event_ids", []))
        if event_id not in confirmed_ids:
            raise PreventUpdate

        full = get_event_full(event_id, logger=app.logger)

        p100 = full.get("p100", [])
        grf = full.get("grf", [])
        footsteps = full.get("footsteps", [])

        view = SummaryView(
            event_id,
            cmap,
            p100,
            grf,
            footsteps,
            step_p100s=footsteps,  # grid only needs step ids for image URLs
        ).render()

        # store everything so selection.py can use it without API calls
        return view, {"footsteps": footsteps}
