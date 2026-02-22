# frontend/callbacks/metrics_filters.py
from dash import Input, Output, State, callback
from frontend.api import get_swipe_event_summary_metrics, get_date_part
from frontend.views.metrics_graph import MetricsGraph
from dash.exceptions import PreventUpdate


def register(app):
    @callback(
        Output("box-size-scatter-plot", "figure"),
        Input("btn-apply-filters", "n_clicks"),
        Input("metrics_x_axis", "value"),
        Input("metrics_y_axis", "value"),
        State("metrics_filter_participant", "value"),
        State("metrics_filter_participant_open_store", "data"),
        State("metrics_filter_year", "value"),
        State("metrics_filter_month", "value"),
        State("metrics_filter_day", "value"),
        prevent_initial_call=True,
    )
    def apply_participant_filter(
        _n,
        x_key,
        y_key,
        selected_participants,
        is_open,
        year,
        month,
        day,
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

        if year:
            filters["year"] = year

        if month:
            filters["month"] = month

        if day:
            filters["day"] = day

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
                filters=filters or None,
                logger=app.logger,
            )
            or {}
        )

        # -------------------------------------------------------------
        # No local filtering anymore.
        # Scatter just renders what backend returned.
        # -------------------------------------------------------------
        return MetricsGraph(metrics)._build_scatter(
            x_key=x_key,
            y_key=y_key,
        )

    # ==========================================================
    # DATE FILTER WATERFALL
    # Participant → Year → Month → Day
    # ==========================================================

    # -------------------------
    # YEAR OPTIONS
    # -------------------------
    @callback(
        Output("metrics_filter_year", "options"),
        Output("metrics_filter_year", "value"),
        Input("metrics_filter_participant", "value"),
        prevent_initial_call=False,  # IMPORTANT
    )
    def populate_year_dropdown(selected_participants):
        # If nothing selected OR "__all__", treat as no filter
        participants = None
        if selected_participants and "__all__" not in selected_participants:
            participants = selected_participants

        years = get_date_part(
            "year",
            participants=participants,
            logger=app.logger,
        )

        return (
            [{"label": str(y), "value": y} for y in years],
            None,
        )

    # -------------------------
    # MONTH OPTIONS
    # -------------------------
    @callback(
        Output("metrics_filter_month", "options"),
        Output("metrics_filter_month", "value"),
        Input("metrics_filter_year", "value"),
        Input("metrics_filter_participant", "value"),  # <-- ADD THIS
    )
    def populate_month_dropdown(year, selected_participants):
        if not year:
            return [], None

        participants = None
        if selected_participants and "__all__" not in selected_participants:
            participants = selected_participants

        months = get_date_part(
            "month",
            participants=participants,
            year=year,
            logger=app.logger,
        )

        return (
            [{"label": str(m), "value": m} for m in months],
            None,
        )

    # -------------------------
    # DAY OPTIONS
    # -------------------------
    @callback(
        Output("metrics_filter_day", "options"),
        Output("metrics_filter_day", "value"),
        Input("metrics_filter_month", "value"),
        Input("metrics_filter_year", "value"),
        Input("metrics_filter_participant", "value"),  # <-- ADD THIS
    )
    def populate_day_dropdown(month, year, selected_participants):
        if not year or not month:
            return [], None

        participants = None
        if selected_participants and "__all__" not in selected_participants:
            participants = selected_participants

        days = get_date_part(
            "day",
            participants=participants,
            year=year,
            month=month,
            logger=app.logger,
        )

        return (
            [{"label": str(d), "value": d} for d in days],
            None,
        )
