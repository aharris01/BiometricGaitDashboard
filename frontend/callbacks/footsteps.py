# frontend/callbacks/footsteps.py

from dash import Input, Output, State, Patch, callback
from dash.exceptions import PreventUpdate

from frontend.api import get_date_bounds, get_participants, search_footsteps
from frontend.views.footstep_view import render_footstep_cards, render_footstep_empty


# -------------------------------------------------
# Small display helpers
# -------------------------------------------------


def _status_text(loaded: int, total: int) -> str:
    # Build the status text shown above the footstep results grid.
    return f"Showing {loaded} of {total} footsteps"


# -------------------------------------------------
# Footstep page callbacks
# -------------------------------------------------


def register(app):
    # -------------------------------------------------
    # Filter setup / reset
    # -------------------------------------------------

    @callback(
        Output("footstep-participant-filter", "options"),
        Input("page-load", "n_intervals"),
        prevent_initial_call=False,
    )
    def load_footstep_participant_options(_n_intervals):
        # Load available participant options when the page first initializes.
        return get_participants(logger=app.logger) or []

    @callback(
        Output("footstep-date-range-filter", "min_date_allowed"),
        Output("footstep-date-range-filter", "max_date_allowed"),
        Input("footstep-participant-filter", "value"),
        prevent_initial_call=False,
    )
    def update_footstep_date_bounds(participants):
        # Update the allowed date range whenever the participant filter changes.
        # This keeps the date picker limited to valid values for the current selection.
        bounds = get_date_bounds(participants=participants, logger=app.logger) or {}
        return (
            bounds.get("min_date"),
            bounds.get("max_date"),
        )

    @callback(
        Output("footstep-participant-filter", "value"),
        Output("footstep-date-range-filter", "start_date"),
        Output("footstep-date-range-filter", "end_date"),
        Output("footstep-height-slider", "value"),
        Output("footstep-width-slider", "value"),
        Output("footstep-size-slider", "value"),
        Input("btn-clear-footstep-filters", "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_footstep_filters(_n_clicks):
        # Reset all footstep view filters back to their default values.
        return (
            [],
            None,
            None,
            [10, 150],
            [10, 130],
            [0, 10000],
        )

    # -------------------------------------------------
    # Initial footstep search
    # -------------------------------------------------

    @callback(
        Output("footstep-results-grid", "children"),
        Output("footstep-results-status", "children"),
        Output("footstep-load-more-wrap", "style"),
        Output("footstep-pagination-store", "data"),
        Input("btn-apply-footstep-filters", "n_clicks"),
        State("footstep-size-slider", "value"),
        State("footstep-participant-filter", "value"),
        State("footstep-date-range-filter", "start_date"),
        State("footstep-date-range-filter", "end_date"),
        State("footstep-height-slider", "value"),
        State("footstep-width-slider", "value"),
        prevent_initial_call=True,
    )
    def apply_footstep_filters(
        _n_clicks,
        size_range,
        participants,
        start_date,
        end_date,
        height_range,
        width_range,
    ):
        # Convert slider values into explicit min/max numbers before passing
        # them into the API search call.
        size_min = None
        size_max = None
        height_min = None
        height_max = None
        width_min = None
        width_max = None

        if isinstance(size_range, (list, tuple)) and len(size_range) == 2:
            size_min = int(size_range[0])
            size_max = int(size_range[1])

        if isinstance(height_range, (list, tuple)) and len(height_range) == 2:
            height_min = int(height_range[0])
            height_max = int(height_range[1])

        if isinstance(width_range, (list, tuple)) and len(width_range) == 2:
            width_min = int(width_range[0])
            width_max = int(width_range[1])

        # Start a new search from the first page of results.
        limit = 60

        result = search_footsteps(
            event_ids=None,
            participants=participants or None,
            date_from=start_date,
            date_to=end_date,
            width_min=width_min,
            width_max=width_max,
            height_min=height_min,
            height_max=height_max,
            size_min=size_min,
            size_max=size_max,
            offset=0,
            limit=limit,
            logger=app.logger,
        ) or {"items": [], "total": 0}

        items = result.get("items", [])
        total = int(result.get("total", 0))

        # Render either cards or an empty-state message.
        children = (
            render_footstep_cards(items)
            if items
            else render_footstep_empty("No matching footsteps.")
        )

        # Only show the Load More button if there are more results to fetch.
        load_more_style = (
            {"display": "block", "marginTop": "12px"}
            if total > len(items)
            else {"display": "none"}
        )

        # Save the active filters in pagination_store so later "load more"
        # requests can continue using the same filter set.
        return (
            children,
            _status_text(len(items), total),
            load_more_style,
            {
                "offset": len(items),
                "limit": limit,
                "total": total,
                "applied": True,
                "participants": participants or [],
                "start_date": start_date,
                "end_date": end_date,
                "height_range": height_range or [10, 150],
                "width_range": width_range or [10, 130],
                "size_range": size_range or [0, 10000],
            },
        )

    # -------------------------------------------------
    # Pagination / load more
    # -------------------------------------------------

    @callback(
        Output("footstep-results-grid", "children", allow_duplicate=True),
        Output("footstep-results-status", "children", allow_duplicate=True),
        Output("footstep-load-more-wrap", "style", allow_duplicate=True),
        Output("footstep-pagination-store", "data", allow_duplicate=True),
        Input("btn-load-more-footsteps", "n_clicks"),
        State("footstep-pagination-store", "data"),
        prevent_initial_call=True,
    )
    def load_more_footsteps(_n_clicks, pagination_store):
        # Do nothing if no search has been applied yet.
        if not pagination_store or not pagination_store.get("applied"):
            raise PreventUpdate

        offset = int(pagination_store.get("offset", 0))
        limit = int(pagination_store.get("limit", 60))
        total = int(pagination_store.get("total", 0))

        # Stop if all matching results have already been loaded.
        if offset >= total:
            raise PreventUpdate

        # Reuse the most recently applied filter values.
        size_range = pagination_store.get("size_range", [0, 10000])
        height_range = pagination_store.get("height_range", [10, 150])
        width_range = pagination_store.get("width_range", [10, 130])

        size_min = int(size_range[0])
        size_max = int(size_range[1])
        height_min = int(height_range[0])
        height_max = int(height_range[1])
        width_min = int(width_range[0])
        width_max = int(width_range[1])

        result = search_footsteps(
            event_ids=None,
            participants=pagination_store.get("participants") or None,
            date_from=pagination_store.get("start_date"),
            date_to=pagination_store.get("end_date"),
            width_min=width_min,
            width_max=width_max,
            height_min=height_min,
            height_max=height_max,
            size_min=size_min,
            size_max=size_max,
            offset=offset,
            limit=limit,
            logger=app.logger,
        ) or {"items": [], "total": 0}

        items = result.get("items", [])
        if not items:
            raise PreventUpdate

        # Append new cards to the existing results instead of rebuilding
        # the whole grid from scratch.
        patch = Patch()
        for card in render_footstep_cards(items):
            patch.append(card)

        new_offset = offset + len(items)

        load_more_style = (
            {"display": "block", "marginTop": "12px"}
            if new_offset < total
            else {"display": "none"}
        )

        return (
            patch,
            _status_text(new_offset, total),
            load_more_style,
            {
                **pagination_store,
                "offset": new_offset,
            },
        )
