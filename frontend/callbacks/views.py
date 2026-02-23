# frontend/callbacks/views.py
from dash import Input, Output, State, callback, ctx

from frontend.api import get_event_full
from frontend.views.swipe_event_view.metrics_graph import MetricsGraph
from frontend.views.swipe_event_view.summary_view import SummaryView


def _ordered_event_ids(store: dict | None) -> list[str]:
    ordered_ids = []
    seen = set()
    for raw_id in (store or {}).get("event_ids", []):
        if raw_id in (None, ""):
            continue
        event_id = str(raw_id)
        if event_id in seen:
            continue
        seen.add(event_id)
        ordered_ids.append(event_id)
    return ordered_ids


def _visible_count_from_store(page_store: dict | None) -> int:
    try:
        visible_count = int((page_store or {}).get("visible_count", 5))
    except (TypeError, ValueError):
        visible_count = 5
    return max(0, visible_count)


def register(app, *, cmap):
    @callback(
        Output("metrics-graph-container", "children"),
        Input("page-load", "n_intervals"),
        prevent_initial_call=False,
    )
    def display_metrics_graph(_n):
        return MetricsGraph({}).render()

    @callback(
        Output("summary-pagination-store", "data"),
        Input("metrics_confirmed_events_store", "data"),
        Input("btn-load-more-summaries", "n_clicks"),
        State("summary-pagination-store", "data"),
        prevent_initial_call=False,
    )
    def update_summary_pagination(confirmed_store: dict, _n_load: int, page_store: dict):
        total = len(_ordered_event_ids(confirmed_store))
        current_visible = _visible_count_from_store(page_store)

        if ctx.triggered_id == "btn-load-more-summaries":
            return {"visible_count": min(total, current_visible + 5)}

        # Reset to first page whenever confirmed list changes.
        return {"visible_count": min(total, 5)}

    @callback(
        Output("summary-pagination-controls", "style"),
        Output("btn-load-more-summaries", "disabled"),
        Input("metrics_confirmed_events_store", "data"),
        Input("summary-pagination-store", "data"),
        prevent_initial_call=False,
    )
    def display_summary_pagination_controls(confirmed_store: dict, page_store: dict):
        total = len(_ordered_event_ids(confirmed_store))
        if total == 0:
            return {"display": "none"}, True

        visible_count = min(total, _visible_count_from_store(page_store))
        all_loaded = visible_count >= total
        return (
            {
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "flexDirection": "column",
                "gap": "8px",
                "marginTop": "10px",
                "width": "100%",
            },
            all_loaded,
        )

    @callback(
        Output("summary-container", "children"),
        Output("footsteps-store", "data"),
        Output("summary-pagination-status", "children"),
        Output("summary-pagination-loading-sink", "children"),
        Input("metrics_confirmed_events_store", "data"),
        Input("summary-pagination-store", "data"),
        State("event-id-store", "data"),
        prevent_initial_call=False,
    )
    def display_summary_graph(
        confirmed_store: dict, page_store: dict, store_data: dict
    ):
        active_event_id = None
        if isinstance(store_data, str):
            active_event_id = str(store_data)
        elif isinstance(store_data, dict):
            raw_event_id = store_data.get("event_id")
            if raw_event_id is not None:
                active_event_id = str(raw_event_id)

        ordered_ids = _ordered_event_ids(confirmed_store)
        total = len(ordered_ids)

        if not ordered_ids:
            return [], {"by_event": {}, "active_event_id": None}, "", "idle"

        if active_event_id in ordered_ids:
            ordered_ids = [active_event_id] + [
                event_id for event_id in ordered_ids if event_id != active_event_id
            ]

        visible_count = min(len(ordered_ids), _visible_count_from_store(page_store))
        visible_ids = ordered_ids[:visible_count]

        if not visible_ids:
            return (
                [],
                {"by_event": {}, "active_event_id": active_event_id},
                f"Showing 0 of {total}",
                "idle",
            )

        summary_views = []
        footsteps_by_event = {}
        for event_id in visible_ids:
            full = get_event_full(event_id, logger=app.logger)

            p100 = full.get("p100", [])
            grf = full.get("grf", [])
            footsteps = full.get("footsteps", [])
            footsteps_by_event[event_id] = footsteps

            summary_views.append(
                SummaryView(
                    event_id,
                    cmap,
                    p100,
                    grf,
                    footsteps,
                    step_p100s=footsteps,  # grid only needs step ids for image URLs
                ).render()
            )

        # Store per-event footsteps so selection.py can update only the matched view.
        return (
            summary_views,
            {
                "by_event": footsteps_by_event,
                "active_event_id": active_event_id,
            },
            f"Showing {len(visible_ids)} of {total}",
            str(len(visible_ids)),
        )
