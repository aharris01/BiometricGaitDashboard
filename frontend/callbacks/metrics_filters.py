# frontend/callbacks/metrics_filters.py

from dash import Input, Output, State, callback
from dash.exceptions import PreventUpdate

from frontend.api import get_swipe_event_summary_metrics
from frontend.views.metrics_graph import MetricsGraph


def register(app):
    @callback(
        Output("box-size-scatter-plot", "figure"),
        Input("btn-apply-filters", "n_clicks"),
        State("metrics_filter_participant", "value"),
        prevent_initial_call=True,
    )
    def apply_participant_filter(_n, selected_participants):
        metrics = get_swipe_event_summary_metrics(logger=app.logger) or {}

        # Nothing selected (or select-all sentinel) => show everything
        if not selected_participants or "__all__" in selected_participants:
            return MetricsGraph(metrics)._build_scatter()

        selected_set = set(selected_participants)

        filtered = {
            event_id: m
            for event_id, m in metrics.items()
            if m.get("participant") in selected_set
        }

        return MetricsGraph(filtered)._build_scatter()
