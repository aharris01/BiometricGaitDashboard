# frontend/callbacks/metrics_filters.py
from dash import Input, Output, State, callback
from frontend.api import get_swipe_event_summary_metrics
from frontend.views.metrics_graph import MetricsGraph


def register(app):
    @callback(
        Output("box-size-scatter-plot", "figure"),
        Input("btn-apply-filters", "n_clicks"),
        Input("metrics_x_axis", "value"),
        Input("metrics_y_axis", "value"),
        State("metrics_filter_participant", "value"),
        State("metrics_filter_participant_open_store", "data"),
        prevent_initial_call=True,
    )
    def apply_participant_filter(
        _n, x_key, y_key, selected_participants, is_open
    ):
        metrics = get_swipe_event_summary_metrics(logger=app.logger) or {}

        x_key = x_key or "avg_box_size"
        y_key = y_key or "footstep_count"

        if is_open and selected_participants and "__all__" not in selected_participants:
            selected_set = set(selected_participants)
            metrics = {
                event_id: m
                for event_id, m in metrics.items()
                if m.get("participant") in selected_set
            }

        return MetricsGraph(metrics)._build_scatter(x_key=x_key, y_key=y_key)
