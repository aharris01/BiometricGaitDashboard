# frontend/callbacks/views.py
from dash import Input, Output, State, callback

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
        Input("metrics_confirmed_events_store", "data"),
        State("event-id-store", "data"),
        prevent_initial_call=False,
    )
    def display_summary_graph(confirmed_store: dict, store_data: dict):
        active_event_id = None
        if isinstance(store_data, str):
            active_event_id = str(store_data)
        elif isinstance(store_data, dict):
            raw_event_id = store_data.get("event_id")
            if raw_event_id is not None:
                active_event_id = str(raw_event_id)

        # Preserve selection order and de-duplicate IDs.
        ordered_ids = []
        seen = set()
        for raw_id in (confirmed_store or {}).get("event_ids", []):
            if raw_id in (None, ""):
                continue
            event_id = str(raw_id)
            if event_id in seen:
                continue
            seen.add(event_id)
            ordered_ids.append(event_id)

        if not ordered_ids:
            return [], {"by_event": {}, "active_event_id": None}

        if active_event_id in ordered_ids:
            ordered_ids = [active_event_id] + [
                event_id for event_id in ordered_ids if event_id != active_event_id
            ]

        summary_views = []
        footsteps_by_event = {}
        for event_id in ordered_ids:
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
        return summary_views, {
            "by_event": footsteps_by_event,
            "active_event_id": active_event_id,
        }
