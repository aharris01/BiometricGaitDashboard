# frontend/callbacks/footsteps.py

from dash import Input, Output, State, Patch, callback
from dash.exceptions import PreventUpdate

from frontend.api import search_footsteps
from frontend.views.footstep_view import render_footstep_cards, render_footstep_empty


def _status_text(loaded: int, total: int) -> str:
    return f"Showing {loaded} of {total} footsteps"


def register(app):
    @callback(
        Output("footstep-results-grid", "children"),
        Output("footstep-results-status", "children"),
        Output("footstep-load-more-wrap", "style"),
        Output("footstep-pagination-store", "data"),
        Input("btn-apply-footstep-filters", "n_clicks"),
        State("footstep-size-slider", "value"),
        prevent_initial_call=True,
    )
    def apply_footstep_filters(_n_clicks, size_range):
        size_min = None
        size_max = None
        if isinstance(size_range, (list, tuple)) and len(size_range) == 2:
            size_min = int(size_range[0])
            size_max = int(size_range[1])

        limit = 60

        result = search_footsteps(
            event_ids=None,
            size_min=size_min,
            size_max=size_max,
            offset=0,
            limit=limit,
            logger=app.logger,
        ) or {"items": [], "total": 0}

        items = result.get("items", [])
        total = int(result.get("total", 0))

        children = (
            render_footstep_cards(items)
            if items
            else render_footstep_empty("No matching footsteps.")
        )

        load_more_style = (
            {"display": "block", "marginTop": "12px"}
            if total > len(items)
            else {"display": "none"}
        )

        return (
            children,
            _status_text(len(items), total),
            load_more_style,
            {
                "offset": len(items),
                "limit": limit,
                "total": total,
                "applied": True,
            },
        )

    @callback(
        Output("footstep-results-grid", "children", allow_duplicate=True),
        Output("footstep-results-status", "children", allow_duplicate=True),
        Output("footstep-load-more-wrap", "style", allow_duplicate=True),
        Output("footstep-pagination-store", "data", allow_duplicate=True),
        Input("btn-load-more-footsteps", "n_clicks"),
        State("footstep-size-slider", "value"),
        State("footstep-pagination-store", "data"),
        prevent_initial_call=True,
    )
    def load_more_footsteps(_n_clicks, size_range, pagination_store):
        if not pagination_store or not pagination_store.get("applied"):
            raise PreventUpdate

        offset = int(pagination_store.get("offset", 0))
        limit = int(pagination_store.get("limit", 60))
        total = int(pagination_store.get("total", 0))

        if offset >= total:
            raise PreventUpdate

        size_min = None
        size_max = None
        if isinstance(size_range, (list, tuple)) and len(size_range) == 2:
            size_min = int(size_range[0])
            size_max = int(size_range[1])

        result = search_footsteps(
            event_ids=None,
            size_min=size_min,
            size_max=size_max,
            offset=offset,
            limit=limit,
            logger=app.logger,
        ) or {"items": [], "total": 0}

        items = result.get("items", [])
        if not items:
            raise PreventUpdate

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
                "offset": new_offset,
                "limit": limit,
                "total": total,
                "applied": True,
            },
        )
