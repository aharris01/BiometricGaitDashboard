# frontend/callbacks/metrics_filters.py
from dash import Input, Output, State, callback, ctx
from dash.exceptions import PreventUpdate

from frontend.views.swipe_event_view.metrics_graph import MetricsGraph
from frontend.api import (
    get_swipe_event_summary_metrics,
    get_date_part,
    get_date_bounds,
)


def register(app):
    # ------------------------------------------------------------
    # 1) Track last-used date filter mode: "parts" vs "range"
    #    IMPORTANT: DatePickerRange triggers via prop_id suffix
    # ------------------------------------------------------------
    @callback(
        Output("metrics_date_filter_mode_store", "data"),
        Input("metrics_filter_year", "value"),
        Input("metrics_filter_month", "value"),
        Input("metrics_filter_day", "value"),
        Input("metrics_filter_date_range", "start_date"),
        Input("metrics_filter_date_range", "end_date"),
        State("metrics_date_filter_mode_store", "data"),
        prevent_initial_call=True,
    )
    def set_last_used_date_filter_mode(
        year, month, day, start_date, end_date, mode_store
    ):
        if not ctx.triggered:
            return mode_store or {"mode": "parts"}

        prop_id = ctx.triggered[0]["prop_id"]  # e.g. "metrics_filter_date_range.end_date"

        # user interacted with the range picker last
        if prop_id.startswith("metrics_filter_date_range."):
            if start_date or end_date:
                return {"mode": "range"}
            return {"mode": "parts"}

        # user interacted with the year/month/day last
        if prop_id.startswith("metrics_filter_year.") or prop_id.startswith(
            "metrics_filter_month."
        ) or prop_id.startswith("metrics_filter_day."):
            if year or month or day:
                return {"mode": "parts"}
            if start_date or end_date:
                return {"mode": "range"}
            return {"mode": "parts"}

        return mode_store or {"mode": "parts"}

    # ------------------------------------------------------------
    # 2) Date bounds for calendar (restricted to available data)
    #    Update bounds when participants change
    # ------------------------------------------------------------
    @callback(
        Output("metrics_filter_date_range", "min_date_allowed"),
        Output("metrics_filter_date_range", "max_date_allowed"),
        Output("metrics_filter_date_range", "initial_visible_month"),
        Output("metrics_filter_date_range", "start_date", allow_duplicate=True),
        Output("metrics_filter_date_range", "end_date", allow_duplicate=True),
        Input("metrics_filter_participant", "value"),
        State("metrics_filter_date_range", "start_date"),
        State("metrics_filter_date_range", "end_date"),
        prevent_initial_call="initial_duplicate",
    )
    def update_date_range_bounds(selected_participants, start_date, end_date):
        participants = None
        if selected_participants and "__all__" not in selected_participants:
            participants = selected_participants

        bounds = get_date_bounds(participants=participants, logger=app.logger) or {}
        min_date = bounds.get("min_date")
        max_date = bounds.get("max_date")

        if not min_date or not max_date:
            return None, None, None, None, None

        def in_bounds(d: str | None) -> bool:
            if not d:
                return True
            return min_date <= d <= max_date

        new_start = start_date if in_bounds(start_date) else None
        new_end = end_date if in_bounds(end_date) else None

        initial_visible = new_end or new_start or min_date

        return min_date, max_date, initial_visible, new_start, new_end

    # ------------------------------------------------------------
    # 3) "From defaults to To" when user picks To first
    #    NOTE: allow_duplicate because bounds callback also writes start_date
    # ------------------------------------------------------------
    @callback(
        Output("metrics_filter_date_range", "start_date", allow_duplicate=True),
        Input("metrics_filter_date_range", "end_date"),
        State("metrics_filter_date_range", "start_date"),
        prevent_initial_call=True,
    )
    def default_from_to_to(end_date, start_date):
        if end_date and not start_date:
            return end_date
        raise PreventUpdate

    # -------------------------------------------------------------
    # Scatter plot: apply filters (participants AND last-used date mode)
    # -------------------------------------------------------------
    @callback(
        Output("box-size-scatter-plot", "figure"),
        Input("btn-apply-filters", "n_clicks"),
        Input("btn-clear-filters", "n_clicks"),
        Input("metrics_x_axis", "value"),
        Input("metrics_y_axis", "value"),
        State("metrics_filter_participant", "value"),
        State("metrics_filter_participant_open_store", "data"),
        State("metrics_scatter_selection_store", "data"),
        State("metrics_selected_events_store", "data"),
        State("event-id-store", "data"),
        # date parts
        State("metrics_filter_year", "value"),
        State("metrics_filter_month", "value"),
        State("metrics_filter_day", "value"),
        # date range
        State("metrics_filter_date_range", "start_date"),
        State("metrics_filter_date_range", "end_date"),
        # last-used mode
        State("metrics_date_filter_mode_store", "data"),
        prevent_initial_call=True,
    )
    def apply_participant_filter(
        _n,
        _n_clear,
        x_key,
        y_key,
        selected_participants,
        is_open,
        scatter_selection_store,
        selected_events_store,
        event_store,
        year,
        month,
        day,
        start_date,
        end_date,
        mode_store,
    ):
        if not x_key or not y_key:
            raise PreventUpdate

        filters = {}

        if ctx.triggered_id != "btn-clear-filters":
        # participants always AND
            if is_open and selected_participants and "__all__" not in selected_participants:
                filters["participants"] = selected_participants

            mode = (mode_store or {}).get("mode", "parts")

            # last-used wins: range vs parts
            if mode == "range" and (start_date or end_date):
                if start_date:
                    filters["date_from"] = start_date
                if end_date:
                    filters["date_to"] = end_date
            else:
                if year:
                    filters["year"] = year
                if month:
                    filters["month"] = month
                if day:
                    filters["day"] = day

        metrics = (
            get_swipe_event_summary_metrics(
                x_key,
                y_key,
                filters=filters or None,
                logger=app.logger,
            )
            or {}
        )

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

    # ==========================================================
    # Existing DATE PART WATERFALL stays the same
    # Participant → Year → Month → Day
    # ==========================================================

    @callback(
        Output("metrics_filter_year", "options"),
        Output("metrics_filter_year", "value"),
        Input("metrics_filter_participant", "value"),
        prevent_initial_call=False,
    )
    def populate_year_dropdown(selected_participants):
        participants = None
        if selected_participants and "__all__" not in selected_participants:
            participants = selected_participants

        years = get_date_part("year", participants=participants, logger=app.logger)
        return ([{"label": str(y), "value": y} for y in years], None)

    @callback(
        Output("metrics_filter_month", "options"),
        Output("metrics_filter_month", "value"),
        Input("metrics_filter_year", "value"),
        Input("metrics_filter_participant", "value"),
        prevent_initial_call=False,
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
        return ([{"label": str(m), "value": m} for m in months], None)

    @callback(
        Output("metrics_filter_day", "options"),
        Output("metrics_filter_day", "value"),
        Input("metrics_filter_month", "value"),
        Input("metrics_filter_year", "value"),
        Input("metrics_filter_participant", "value"),
        prevent_initial_call=False,
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
        return ([{"label": str(d), "value": d} for d in days], None)
    

    @callback(
        Output("metrics_filter_participant", "value", allow_duplicate=True),
        Output("metrics_filter_participant_state", "data", allow_duplicate=True),
        Output("metrics_filter_year", "value", allow_duplicate=True),
        Output("metrics_filter_month", "value", allow_duplicate=True),
        Output("metrics_filter_day", "value", allow_duplicate=True),
        Output("metrics_filter_date_range", "start_date", allow_duplicate=True),
        Output("metrics_filter_date_range", "end_date", allow_duplicate=True),
        Output("metrics_date_filter_mode_store", "data", allow_duplicate=True),
        Input("btn-clear-filters", "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_all_filters(_):
        return (
            [],            # participants
            {"prev": []},  # reset select-all memory (important)
            None,          # year
            None,          # month
            None,          # day
            None,          # range start
            None,          # range end
            {"mode": "parts"},  # reset mode
        )