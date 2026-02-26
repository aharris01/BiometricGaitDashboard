from dash import Input, Output, Patch, State, callback, ctx, no_update

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


def _existing_footsteps_by_event(store: dict | None) -> dict[str, list]:
    if not isinstance(store, dict):
        return {}

    raw_by_event = store.get("by_event")
    if not isinstance(raw_by_event, dict):
        return {}

    by_event = {}
    for raw_id, footsteps in raw_by_event.items():
        if raw_id in (None, ""):
            continue
        by_event[str(raw_id)] = footsteps if isinstance(footsteps, list) else []
    return by_event


def _active_event_id_from_store(store_data: dict | str | None) -> str | None:
    if isinstance(store_data, str):
        return str(store_data)
    if isinstance(store_data, dict):
        raw_event_id = store_data.get("event_id")
        if raw_event_id is not None:
            return str(raw_event_id)
    return None


def _summary_store_payload(
    by_event: dict[str, list], active_event_id: str | None
) -> dict:
    return {"by_event": by_event, "active_event_id": active_event_id}


def _summary_queue_payload(
    *, pending_ids: list, total: int, visible_total: int
) -> dict:
    return {"pending_ids": pending_ids, "total": total, "visible_total": visible_total}


def _summary_status_text(loaded: int, total: int) -> str:
    return f"Showing {loaded} of {total}"


def _normalized_queue_state(
    render_queue_store: dict | None, *, fallback_total: int, existing_count: int
) -> tuple[list, int, int]:
    queue_store = render_queue_store or {}
    pending_ids = list(queue_store.get("pending_ids", []))

    queued_total = queue_store.get("total", fallback_total)
    queued_visible_total = queue_store.get(
        "visible_total", existing_count + len(pending_ids)
    )

    try:
        queued_total = int(queued_total)
    except (TypeError, ValueError):
        queued_total = fallback_total

    try:
        queued_visible_total = int(queued_visible_total)
    except (TypeError, ValueError):
        queued_visible_total = existing_count + len(pending_ids)

    return pending_ids, queued_total, queued_visible_total


def _render_summary_view(app, *, event_id: str, cmap):
    full = get_event_full(event_id, logger=app.logger)

    p100 = full.get("p100", [])
    grf = full.get("grf", [])
    footsteps = full.get("footsteps", [])

    return (
        SummaryView(
            event_id,
            cmap,
            p100,
            grf,
            footsteps,
            step_p100s=footsteps,  # grid only needs step ids for image URLs
        ).render(),
        footsteps,
    )


def register(app, *, cmap):
    @callback(
        Output("metrics-graph-container", "children"),
        Input("page-load", "n_intervals"),
        prevent_initial_call=False,
    )
    def display_metrics_graph(_n):
        return MetricsGraph({}).render()

    # ------------------------------------------------------------
    # Pagination state: visible_count
    # ------------------------------------------------------------
    @callback(
        Output("summary-pagination-store", "data"),
        Input("metrics_confirmed_events_store", "data"),
        Input("btn-load-more-summaries", "n_clicks"),
        State("summary-pagination-store", "data"),
        prevent_initial_call=False,
    )
    def update_summary_pagination(
        confirmed_store: dict, _n_load: int, page_store: dict
    ):
        total = len(_ordered_event_ids(confirmed_store))
        current_visible = _visible_count_from_store(page_store)

        if ctx.triggered_id == "btn-load-more-summaries":
            return {"visible_count": min(total, current_visible + 5)}

        # Reset to first page whenever confirmed list changes.
        return {"visible_count": min(total, 5)}

    # ------------------------------------------------------------
    # Show/hide pagination controls
    # ------------------------------------------------------------
    @callback(
        Output("summary-pagination-controls", "style"),
        Output("btn-load-more-summaries", "disabled"),
        Output("summary-pagination-load-wrap", "style"),
        Input("metrics_confirmed_events_store", "data"),
        Input("summary-pagination-store", "data"),
        prevent_initial_call=False,
    )
    def display_summary_pagination_controls(confirmed_store: dict, page_store: dict):
        total = len(_ordered_event_ids(confirmed_store))
        if total == 0:
            return {"display": "none"}, True, {"display": "none"}

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
            {"display": "none"} if all_loaded else {"display": "block"},
        )

    # ------------------------------------------------------------
    # Render summary cards incrementally (queue + interval)
    # ------------------------------------------------------------
    @callback(
        Output("summary-container", "children"),
        Output("footsteps-store", "data"),
        Output("summary-pagination-status", "children"),
        Output("summary-pagination-loading-sink", "children"),
        Output("summary-render-queue-store", "data"),
        Output("summary-render-interval", "max_intervals"),
        Input("metrics_confirmed_events_store", "data"),
        Input("summary-pagination-store", "data"),
        Input("summary-render-interval", "n_intervals"),
        State("event-id-store", "data"),
        State("footsteps-store", "data"),
        State("summary-render-queue-store", "data"),
        prevent_initial_call=False,
    )
    def display_summary_graph(
        confirmed_store: dict,
        page_store: dict,
        _render_tick: int,
        store_data: dict,
        existing_footsteps_store: dict,
        render_queue_store: dict,
    ):
        active_event_id = _active_event_id_from_store(store_data)
        ordered_ids = _ordered_event_ids(confirmed_store)
        total = len(ordered_ids)

        if not ordered_ids:
            return (
                [],
                _summary_store_payload({}, None),
                "",
                "idle",
                _summary_queue_payload(pending_ids=[], total=0, visible_total=0),
                _render_tick,
            )

        # Put active event first if it exists in confirmed list
        if active_event_id in ordered_ids:
            ordered_ids = [active_event_id] + [
                event_id for event_id in ordered_ids if event_id != active_event_id
            ]

        visible_total = min(total, _visible_count_from_store(page_store))
        visible_ids = ordered_ids[:visible_total]
        existing_by_event = _existing_footsteps_by_event(existing_footsteps_store)

        if not visible_ids:
            return (
                [],
                _summary_store_payload({}, active_event_id),
                _summary_status_text(0, total),
                "idle",
                _summary_queue_payload(pending_ids=[], total=total, visible_total=0),
                _render_tick,
            )

        # -----------------------------
        # Interval tick: render next item in queue
        # -----------------------------
        if ctx.triggered_id == "summary-render-interval":
            pending_ids, queued_total, queued_visible_total = _normalized_queue_state(
                render_queue_store,
                fallback_total=total,
                existing_count=len(existing_by_event),
            )

            if not pending_ids:
                loaded = min(len(existing_by_event), queued_visible_total)
                return (
                    no_update,
                    _summary_store_payload(existing_by_event, active_event_id),
                    _summary_status_text(loaded, queued_total),
                    "idle",
                    _summary_queue_payload(
                        pending_ids=[],
                        total=queued_total,
                        visible_total=queued_visible_total,
                    ),
                    _render_tick,
                )

            event_id = str(pending_ids[0])
            event_view, footsteps = _render_summary_view(
                app, event_id=event_id, cmap=cmap
            )

            merged_by_event = dict(existing_by_event)
            merged_by_event[event_id] = footsteps

            rest = pending_ids[1:]
            loaded_count = max(0, queued_visible_total - len(rest))

            patch = Patch()
            patch.append(event_view)

            return (
                patch,
                _summary_store_payload(merged_by_event, active_event_id),
                _summary_status_text(loaded_count, queued_total),
                str(loaded_count),
                _summary_queue_payload(
                    pending_ids=rest,
                    total=queued_total,
                    visible_total=queued_visible_total,
                ),
                (_render_tick + 1) if rest else _render_tick,
            )

        # -----------------------------
        # Non-interval triggers: decide whether to rebuild or append
        # -----------------------------
        existing_ids = list(existing_by_event.keys())
        can_append_only = (
            bool(existing_ids)
            and len(visible_ids) > len(existing_ids)
            and visible_ids[: len(existing_ids)] == existing_ids
        )

        if can_append_only:
            base_by_event = dict(existing_by_event)
            pending_ids = visible_ids[len(existing_ids) :]
        else:
            base_by_event = {}
            pending_ids = list(visible_ids)

        if not pending_ids:
            loaded = len(base_by_event) if can_append_only else len(visible_ids)
            return (
                no_update if can_append_only else [],
                _summary_store_payload(base_by_event, active_event_id),
                _summary_status_text(loaded, total),
                "idle",
                _summary_queue_payload(
                    pending_ids=[],
                    total=total,
                    visible_total=len(visible_ids),
                ),
                _render_tick,
            )

        # Render first immediately, queue the rest for interval
        first_id = str(pending_ids[0])
        event_view, footsteps = _render_summary_view(app, event_id=first_id, cmap=cmap)
        base_by_event[first_id] = footsteps

        rest = pending_ids[1:]
        loaded_count = len(visible_ids) - len(rest)

        if can_append_only:
            summary_output = Patch()
            summary_output.append(event_view)
        else:
            summary_output = [event_view]

        return (
            summary_output,
            _summary_store_payload(base_by_event, active_event_id),
            _summary_status_text(loaded_count, total),
            str(loaded_count),
            _summary_queue_payload(
                pending_ids=rest,
                total=total,
                visible_total=len(visible_ids),
            ),
            (_render_tick + 1) if rest else _render_tick,
        )
