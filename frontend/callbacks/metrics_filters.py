# frontend/callbacks/metrics_filters.py
from dash import Input, Output, State, callback
from frontend.api import get_swipe_event_summary_metrics
from frontend.views.swipe_event_view.metrics_graph import MetricsGraph
from dash.exceptions import PreventUpdate


def register(app):
    @callback(
        Output("box-size-scatter-plot", "figure"),
        Input("btn-apply-filters", "n_clicks"),
        Input("metrics_x_axis", "value"),
        Input("metrics_y_axis", "value"),
        State("metrics_filter_participant", "value"),
        State("metrics_filter_participant_open_store", "data"),
        State("metrics_scatter_selection_store", "data"),
        State("metrics_selected_events_store", "data"),
        State("event-id-store", "data"),
        prevent_initial_call=True,
    )
    def apply_participant_filter(
        _n,
        x_key,
        y_key,
        selected_participants,
        is_open,
        scatter_selection_store,
        selected_events_store,
        event_store,
    ):
        # -------------------------------------------------------------
        # Require both axes to be selected before querying backend
        # -------------------------------------------------------------
        if not x_key or not y_key:
            raise PreventUpdate

        # -------------------------------------------------------------
        # Build backend filter dictionary
        #
        # We no longer filter locally.
        # Instead, we pass filters to the backend and let SQL handle it.
        # -------------------------------------------------------------
        filters = {}

        if is_open and selected_participants and "__all__" not in selected_participants:
            filters["participants"] = selected_participants

        # -------------------------------------------------------------
        # Fetch filtered dataset from backend
        #
        # Backend now:
        # - joins swipe_event + global_metrics
        # - applies participant filter in SQL
        # - returns only requested x/y metrics
        # -------------------------------------------------------------
        metrics = (
            get_swipe_event_summary_metrics(
                x_key,
                y_key,
                filters=filters or None,  # <-- NEW
                logger=app.logger,
            )
            or {}
        )

        # -------------------------------------------------------------
        # No local filtering anymore.
        # Scatter just renders what backend returned.
        # -------------------------------------------------------------
        pending_event_ids = (scatter_selection_store or {}).get("event_ids", [])
        selected_event_ids = (selected_events_store or {}).get("event_ids", [])
        active_event_id = (event_store or {}).get("event_id")

        return MetricsGraph(metrics)._build_scatter(
            x_key=x_key,
            y_key=y_key,
            pending_event_ids=pending_event_ids,
            selected_event_ids=selected_event_ids,
            active_event_id=active_event_id,
        )
