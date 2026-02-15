# frontend/callbacks/metrics_filters.py

from dash import Input, Output, State, callback

from frontend.api import get_swipe_event_summary_metrics
from frontend.views.metrics_graph import MetricsGraph


def register(app):
    @callback(
        Output("box-size-scatter-plot", "figure"),
        Input("btn-apply-filters", "n_clicks"),
        State("metrics_filter_participant", "value"),
        State("metrics_filter_participant_open_store", "data"),
        State("metrics_x_axis", "value"),
        State("metrics_y_axis", "value"),
        prevent_initial_call=True,
    )
    def apply_participant_filter(_n, selected_participants, is_open, x_key, y_key):
        metrics = get_swipe_event_summary_metrics(logger=app.logger) or {}

        # default safety
        x_key = x_key or "avg_box_size"
        y_key = y_key or "footstep_count"

        if not is_open:
            return MetricsGraph(metrics)._build_scatter(x_key, y_key)

        if not selected_participants or "__all__" in selected_participants:
            return MetricsGraph(metrics)._build_scatter(x_key, y_key)

        selected_set = set(selected_participants)
        filtered = {
            event_id: m
            for event_id, m in metrics.items()
            if m.get("participant") in selected_set
        }
        return MetricsGraph(filtered)._build_scatter(x_key, y_key)

