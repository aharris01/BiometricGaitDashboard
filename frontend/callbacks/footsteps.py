# frontend/callbacks/footsteps.py
from dash import ALL, MATCH, Input, Output, State, callback, ctx, html, no_update
from dash.exceptions import PreventUpdate
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from frontend.api import (
    create_draft_footstep,
    create_footstep,
    delete_footstep,
    get_date_bounds,
    get_footstep_details,
    get_footstep_review,
    get_participants,
    save_footstep_review,
    search_footsteps,
)
from frontend.views.footstep_view import (
    _footstep_thumbnail_src,
    render_footstep_cards,
    render_footstep_empty,
)


def _empty_review():
    return {
        "open": False,
        "event_id": None,
        "footstep_id": None,
        "review": None,
        "message": None,
        "create_mode": False,
    }


def _open_review(event_id: str, footstep_id: int, review: dict, message: str):
    return {
        "open": True,
        "event_id": event_id,
        "footstep_id": footstep_id,
        "review": review,
        "message": message,
        "create_mode": False,
    }


def _empty_context():
    return {
        "open": False,
        "event_id": None,
        "footstep_id": None,
        "details": None,
    }


def _status_text(loaded: int, total: int) -> str:
    return f"Showing {loaded} of {total} footsteps"


def _thumbnail_revision_key(event_id: str, footstep_id: int) -> str:
    return f"{event_id}:{footstep_id}"


def _load_more_style(loaded: int, total: int) -> dict[str, str]:
    return (
        {"display": "block", "marginTop": "12px"}
        if loaded < total
        else {"display": "none"}
    )


def _find_step_number(
    items: list[dict] | None,
    *,
    event_id: str,
    footstep_id: int,
) -> int | None:
    for item in items or []:
        if (
            str(item.get("event_id")) == event_id
            and int(item.get("footstep_id", -1)) == footstep_id
        ):
            step_number = item.get("step_number")
            return int(step_number) if step_number is not None else None

    return None


def _find_footstep_index(
    items: list[dict] | None,
    *,
    event_id: str,
    footstep_id: int,
) -> int | None:
    for index, item in enumerate(items or []):
        if (
            str(item.get("event_id")) == event_id
            and int(item.get("footstep_id", -1)) == footstep_id
        ):
            return index

    return None


def _refresh_thumbnail_revisions_for_event(
    thumbnail_revisions: dict[str, int] | None,
    *,
    event_id: str,
    items: list[dict] | None,
) -> dict[str, int]:
    current_revisions = thumbnail_revisions or {}
    refreshed = {
        revision_key: revision
        for revision_key, revision in current_revisions.items()
        if not revision_key.startswith(f"{event_id}:")
    }

    for item in items or []:
        if str(item["event_id"]) != event_id:
            continue

        revision_key = _thumbnail_revision_key(event_id, int(item["footstep_id"]))
        refreshed[revision_key] = int(current_revisions.get(revision_key, 0)) + 1

    return refreshed


def _to_int(value, fallback: int) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return fallback


def _search_footsteps_for_pagination(
    pagination_store: dict | None,
    *,
    limit: int,
    logger,
) -> tuple[list[dict], int] | tuple[None, None]:
    if not pagination_store or not pagination_store.get("applied"):
        return None, None

    size_range = pagination_store.get("size_range", [0, 10000])
    height_range = pagination_store.get("height_range", [10, 150])
    width_range = pagination_store.get("width_range", [10, 130])

    result = search_footsteps(
        event_ids=None,
        participants=pagination_store.get("participants") or None,
        date_from=pagination_store.get("start_date"),
        date_to=pagination_store.get("end_date"),
        width_min=int(width_range[0]),
        width_max=int(width_range[1]),
        height_min=int(height_range[0]),
        height_max=int(height_range[1]),
        size_min=int(size_range[0]),
        size_max=int(size_range[1]),
        offset=0,
        limit=max(1, int(limit)),
        logger=logger,
    ) or {"items": [], "total": 0}

    return result.get("items", []), int(result.get("total", 0))


def _refresh_visible_results_for_created_footstep(
    pagination_store: dict | None,
    visible_items: list[dict] | None,
    *,
    event_id: str,
    footstep_id: int,
    logger,
) -> tuple[dict, list[dict]] | tuple[None, None]:
    if not pagination_store or not pagination_store.get("applied"):
        return None, None

    visible_count = max(1, len(visible_items or []))
    request_limit = visible_count
    base_target_count = visible_count + 1
    latest_items: list[dict] = []
    latest_total = int(pagination_store.get("total", visible_count))

    while True:
        search_items, search_total = _search_footsteps_for_pagination(
            pagination_store,
            limit=request_limit,
            logger=logger,
        )
        latest_items = search_items or []
        latest_total = int(search_total or 0)

        created_index = _find_footstep_index(
            latest_items,
            event_id=event_id,
            footstep_id=footstep_id,
        )
        if created_index is not None:
            target_count = max(base_target_count, created_index + 1)
            if len(latest_items) >= target_count:
                latest_items = latest_items[:target_count]
                break
        else:
            target_count = base_target_count

        if request_limit >= latest_total:
            break

        next_limit = min(
            latest_total,
            max(target_count, request_limit + 1, request_limit * 2),
        )
        if next_limit == request_limit:
            break

        request_limit = next_limit

    return (
        {
            **pagination_store,
            "offset": len(latest_items),
            "total": latest_total,
        },
        latest_items,
    )


def _review_label_value(value) -> str:
    if value is None:
        return ""
    return str(value)


def _get_bbox(review: dict, x_min=None, x_max=None, y_min=None, y_max=None):
    saved = review.get("bbox") or {}

    left = _to_int(x_min, saved.get("x_min", 0))
    right = _to_int(x_max, saved.get("x_max", 1))
    top = _to_int(y_min, saved.get("y_min", 0))
    bottom = _to_int(y_max, saved.get("y_max", 1))

    if left > right:
        left, right = right, left

    if top > bottom:
        top, bottom = bottom, top

    return {
        "x_min": left,
        "x_max": right,
        "y_min": top,
        "y_max": bottom,
    }


def _make_figure(review: dict, bbox: dict, cmap):
    p100 = review.get("event_p100") or []

    fig = px.imshow(
        p100,
        zmin=0,
        zmax=max(max(row) for row in p100) if p100 else 1,
        color_continuous_scale=cmap,
    )

    if p100:
        fig.add_shape(
            type="rect",
            x0=bbox["x_min"],
            x1=bbox["x_max"],
            y0=bbox["y_min"],
            y1=bbox["y_max"],
            line={"color": "#00ff66", "width": 2},
        )

    fig.update_layout(
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        dragmode="drawrect",
        coloraxis_showscale=False,
        uirevision=True,
    )

    fig.update_xaxes(showgrid=False, zeroline=False, constrain="domain")
    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
        autorange="reversed",
        scaleanchor="x",
        constrain="domain",
    )

    return fig


def _render_history(changes: list[dict]):
    if not changes:
        return "No local changes yet."

    items = []
    for change in changes:
        items.append(
            html.Div(
                className="footstep-history-item",
                children=[
                    html.Div(
                        f"{change['changed_at']} · {change['action']}",
                        className="footstep-history-time",
                    ),
                    html.Div(
                        f"BBox: "
                        f"({change['old_x_min']}, {change['old_y_min']}) - "
                        f"({change['old_x_max']}, {change['old_y_max']}) "
                        f"→ "
                        f"({change['new_x_min']}, {change['new_y_min']}) - "
                        f"({change['new_x_max']}, {change['new_y_max']})",
                    ),
                    html.Div(f"Label: {change['old_label']} → {change['new_label']}"),
                ],
            )
        )

    return items


def _placeholder_figure(message: str, *, height: int):
    fig = go.Figure()
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text=message,
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=13, color="#6b7280"),
            )
        ],
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


def _make_context_p100_figure(
    p100: list[list[float]] | None,
    cmap,
    cop_x: list[float] | None = None,
    cop_y: list[float] | None = None,
):
    if not p100:
        return _placeholder_figure("P100 not available for this footstep.", height=360)

    fig = px.imshow(p100, color_continuous_scale=cmap)
    z_max = max(max(row) for row in p100) if p100 else 1
    fig.update_traces(zmin=0, zmax=z_max)
    fig.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=10, b=30),
        coloraxis_showscale=False,
        plot_bgcolor="black",
        paper_bgcolor="white",
    )

    if cop_x and cop_y:
        cop_pairs = [
            (float(x), float(y))
            for x, y in zip(cop_x, cop_y, strict=False)
            if x is not None and y is not None and np.isfinite(x) and np.isfinite(y)
        ]
        if cop_pairs:
            xs = [pair[0] for pair in cop_pairs]
            ys = [pair[1] for pair in cop_pairs]
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="lines+markers",
                    line=dict(color="#ff2bd6", width=2),
                    marker=dict(size=5, color="#ff2bd6"),
                    name="COP Path",
                    legendgroup="cop-overlay",
                    showlegend=True,
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[xs[0]],
                    y=[ys[0]],
                    mode="markers",
                    marker=dict(
                        size=8,
                        color="#22c55e",
                        line=dict(color="#ffffff", width=2),
                    ),
                    name="Start",
                    legendgroup="cop-overlay",
                    text=["Start"],
                    hoverinfo="text",
                    showlegend=True,
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[xs[-1]],
                    y=[ys[-1]],
                    mode="markers",
                    marker=dict(
                        size=8,
                        color="#111827",
                        line=dict(color="#ffffff", width=2),
                    ),
                    name="End",
                    legendgroup="cop-overlay",
                    text=["End"],
                    hoverinfo="text",
                    showlegend=True,
                )
            )

    fig.update_xaxes(constrain="domain", scaleanchor="y", showgrid=False)
    fig.update_yaxes(autorange="reversed", constrain="domain", showgrid=False)
    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=10),
            bgcolor="rgba(255,255,255,0.75)",
            borderwidth=0,
            groupclick="togglegroup",
        )
    )
    return fig


def _make_context_grf_figure(grf: list[float] | None):
    if not grf:
        return _placeholder_figure("GRF not available for this footstep.", height=220)

    fig = go.Figure()
    fig.add_trace(go.Scatter(y=list(grf), mode="lines", line=dict(color="#2563eb")))
    fig.update_layout(
        height=220,
        margin=dict(l=30, r=20, t=10, b=30),
        xaxis_title="Frame",
        yaxis_title="GRF",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


def _make_draft_grf_figure(
    volume: list[list[list[float]]] | None,
    frame_range: list[int] | None,
    *,
    draft_start_frame: int,
):
    if not volume:
        return _placeholder_figure("GRF not available for this draft.", height=420)

    volume_np = np.asarray(volume, dtype=float)
    full_grf = volume_np.reshape(volume_np.shape[0], -1).sum(axis=1)

    if not frame_range or len(frame_range) != 2:
        start_idx = 0
        end_idx = len(full_grf) - 1
    else:
        start_idx = max(0, int(frame_range[0]) - draft_start_frame)
        end_idx = min(len(full_grf) - 1, int(frame_range[1]) - draft_start_frame)

    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx

    frame_axis = np.arange(draft_start_frame, draft_start_frame + len(full_grf))

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=frame_axis,
            y=full_grf,
            mode="lines",
            line=dict(color="#2563eb"),
            name="Draft GRF",
        )
    )
    fig.add_vrect(
        x0=frame_axis[start_idx],
        x1=frame_axis[end_idx],
        fillcolor="rgba(37, 99, 235, 0.14)",
        line_width=0,
    )
    fig.update_layout(
        height=420,
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis_title="Frame",
        yaxis_title="GRF",
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
    )
    return fig


def _make_draft_placeholder_figure(message: str):
    return _placeholder_figure(message, height=420)


def _make_fake_draft_volume(
    *,
    width: int,
    height: int,
    depth: int,
) -> list[list[list[float]]]:
    width = max(8, width)
    height = max(8, height)
    depth = max(2, depth)

    xs = np.arange(width, dtype=float)[None, :]
    ys = np.arange(height, dtype=float)[:, None]
    frames: list[list[list[float]]] = []

    for idx in range(depth):
        center_x = (width - 1) * ((idx + 1) / (depth + 1))
        center_y = (height - 1) * (
            0.35 + 0.3 * np.sin((idx / max(depth - 1, 1)) * np.pi)
        )
        sigma_x = max(width / 5.5, 1.5)
        sigma_y = max(height / 5.5, 1.5)
        frame = np.exp(
            -(
                ((xs - center_x) ** 2) / (2 * sigma_x**2)
                + ((ys - center_y) ** 2) / (2 * sigma_y**2)
            )
        )
        frames.append((frame * (1.0 + 0.1 * idx)).tolist())

    return frames


def _max_projection_in_range(
    volume: list[list[list[float]]] | None,
    start_idx: int,
    end_idx: int,
):
    if not volume:
        return None

    volume_np = np.asarray(volume, dtype=float)
    selected = volume_np[start_idx : end_idx + 1, :, :]
    if selected.shape[0] == 0:
        return None
    return np.max(selected, axis=0)


def _make_draft_preview_figure(
    volume: list[list[list[float]]] | None,
    depth_range: list[int] | None,
    cmap,
):
    if not volume:
        return _make_draft_placeholder_figure("Loading draft preview...")

    if not depth_range or len(depth_range) != 2:
        depth_range = [0, len(volume) - 1]

    start_idx = max(0, int(depth_range[0]))
    end_idx = min(len(volume) - 1, int(depth_range[1]))
    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx

    projected = _max_projection_in_range(volume, start_idx, end_idx)
    if projected is None:
        return _make_draft_placeholder_figure("Draft preview is empty.")

    volume_np = np.asarray(volume, dtype=float)
    fig = px.imshow(
        projected,
        color_continuous_scale=cmap,
        zmin=float(np.min(volume_np)),
        zmax=float(np.max(volume_np)),
    )
    fig.update_layout(
        height=420,
        margin=dict(l=20, r=20, t=20, b=20),
        coloraxis_showscale=False,
    )
    fig.update_xaxes(constrain="domain", scaleanchor="y")
    fig.update_yaxes(autorange="reversed", constrain="domain")
    return fig


def _resolve_draft_depth_range(
    *,
    slider_max: int,
    depth_range: list[int] | None,
    reset_range: bool,
) -> list[int]:
    if reset_range or not depth_range or len(depth_range) != 2:
        return [0, slider_max]

    start_idx = max(0, min(slider_max, int(depth_range[0])))
    end_idx = max(0, min(slider_max, int(depth_range[1])))
    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx

    return [start_idx, end_idx]


def _resolve_draft_frame_range(
    *,
    draft_start: int,
    draft_end: int,
    frame_range: list[int] | None,
    reset_range: bool,
) -> list[int]:
    if reset_range or not frame_range or len(frame_range) != 2:
        return [draft_start, draft_end]

    start_frame = max(draft_start, min(draft_end, int(frame_range[0])))
    end_frame = max(draft_start, min(draft_end, int(frame_range[1])))
    if start_frame > end_frame:
        start_frame, end_frame = end_frame, start_frame

    return [start_frame, end_frame]


def _draft_range_to_frame_bounds(
    draft_store: dict | None,
    depth_range: list[int] | None,
) -> tuple[int, int] | None:
    if not draft_store or not draft_store.get("volume"):
        return None

    volume = draft_store["volume"]
    draft_start = int(draft_store.get("start_frame", 0))
    draft_end = draft_start + max(0, len(volume) - 1)
    resolved_range = _resolve_draft_frame_range(
        draft_start=draft_start,
        draft_end=draft_end,
        frame_range=depth_range,
        reset_range=False,
    )

    return (
        int(resolved_range[0]),
        int(resolved_range[1]),
    )


def register(app, *, cmap):
    @callback(
        Output("footstep-participant-filter", "options"),
        Input("page-load", "n_intervals"),
        prevent_initial_call=False,
    )
    def load_footstep_participant_options(_n_intervals):
        return get_participants(logger=app.logger) or []

    @callback(
        Output("footstep-date-range-filter", "min_date_allowed"),
        Output("footstep-date-range-filter", "max_date_allowed"),
        Input("footstep-participant-filter", "value"),
        prevent_initial_call=False,
    )
    def update_footstep_date_bounds(participants):
        bounds = get_date_bounds(participants=participants, logger=app.logger) or {}
        return bounds.get("min_date"), bounds.get("max_date")

    @callback(
        Output("footstep-participant-filter", "value"),
        Output("footstep-date-range-filter", "start_date"),
        Output("footstep-date-range-filter", "end_date"),
        Output("footstep-height-slider", "value"),
        Output("footstep-width-slider", "value"),
        Output("footstep-size-slider", "value"),
        Output("footstep-review-store", "data", allow_duplicate=True),
        Input("btn-clear-footstep-filters", "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_footstep_filters(_n_clicks):
        return (
            [],
            None,
            None,
            [10, 150],
            [10, 130],
            [0, 10000],
            _empty_review(),
        )

    @callback(
        Output("footstep-pagination-store", "data"),
        Output("footstep-review-store", "data", allow_duplicate=True),
        Output("footstep-results-store", "data"),
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

        pagination_store = {
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
        }

        return (
            pagination_store,
            _empty_review(),
            items,
        )

    @callback(
        Output("footstep-context-store", "data"),
        Input(
            {"type": "footstep-review-open", "event_id": ALL, "footstep_id": ALL},
            "n_clicks",
        ),
        Input("btn-close-footstep-review", "n_clicks"),
        prevent_initial_call=True,
    )
    def load_footstep_context(_open_clicks, _close_clicks):
        triggered = ctx.triggered_id

        if triggered == "btn-close-footstep-review":
            return _empty_context()

        if not isinstance(triggered, dict):
            raise PreventUpdate

        if triggered.get("type") != "footstep-review-open":
            raise PreventUpdate

        clicked_value = None
        if ctx.inputs_list and isinstance(ctx.inputs_list[0], list):
            for item in ctx.inputs_list[0]:
                if item.get("id") == triggered:
                    clicked_value = item.get("value")
                    break

        if clicked_value in (None, 0):
            raise PreventUpdate

        event_id = str(triggered["event_id"])
        footstep_id = int(triggered["footstep_id"])
        details = get_footstep_details(event_id, footstep_id, logger=app.logger)

        return {
            "open": True,
            "event_id": event_id,
            "footstep_id": footstep_id,
            "details": details,
        }

    @callback(
        Output("footstep-pagination-store", "data", allow_duplicate=True),
        Output("footstep-results-store", "data", allow_duplicate=True),
        Input("btn-load-more-footsteps", "n_clicks"),
        State("footstep-pagination-store", "data"),
        State("footstep-results-store", "data"),
        prevent_initial_call=True,
    )
    def load_more_footsteps(_n_clicks, pagination_store, visible_items):
        if not pagination_store or not pagination_store.get("applied"):
            raise PreventUpdate

        offset = int(pagination_store.get("offset", 0))
        limit = int(pagination_store.get("limit", 60))
        total = int(pagination_store.get("total", 0))

        if offset >= total:
            raise PreventUpdate

        size_range = pagination_store.get("size_range", [0, 10000])
        height_range = pagination_store.get("height_range", [10, 150])
        width_range = pagination_store.get("width_range", [10, 130])

        result = search_footsteps(
            event_ids=None,
            participants=pagination_store.get("participants") or None,
            date_from=pagination_store.get("start_date"),
            date_to=pagination_store.get("end_date"),
            width_min=int(width_range[0]),
            width_max=int(width_range[1]),
            height_min=int(height_range[0]),
            height_max=int(height_range[1]),
            size_min=int(size_range[0]),
            size_max=int(size_range[1]),
            offset=offset,
            limit=limit,
            logger=app.logger,
        ) or {"items": [], "total": 0}

        new_items = result.get("items", [])
        if not new_items:
            raise PreventUpdate

        new_offset = offset + len(new_items)

        return (
            {
                **pagination_store,
                "offset": new_offset,
            },
            [*(visible_items or []), *new_items],
        )

    @callback(
        Output("footstep-results-grid", "children"),
        Output("footstep-results-status", "children"),
        Output("footstep-load-more-wrap", "style"),
        Input("footstep-results-store", "data"),
        State("footstep-pagination-store", "data"),
        State("footstep-thumbnail-revision-store", "data"),
        prevent_initial_call=False,
    )
    def render_footstep_results(
        visible_items,
        pagination_store,
        thumbnail_revisions,
    ):
        if not pagination_store or not pagination_store.get("applied"):
            return (
                render_footstep_empty(
                    "No footsteps loaded yet. Choose filters and press OK."
                ),
                "Choose filters, then press OK.",
                {"display": "none"},
            )

        items = visible_items or []
        total = int(pagination_store.get("total", len(items)))
        children = (
            render_footstep_cards(items, thumbnail_revisions)
            if items
            else render_footstep_empty("No matching footsteps.")
        )

        return (
            children,
            _status_text(len(items), total),
            _load_more_style(len(items), total),
        )

    @callback(
        Output(
            {"type": "footstep-thumbnail", "event_id": MATCH, "footstep_id": MATCH},
            "src",
        ),
        Input("footstep-thumbnail-revision-store", "data"),
        State(
            {"type": "footstep-thumbnail", "event_id": MATCH, "footstep_id": MATCH},
            "id",
        ),
        prevent_initial_call=True,
    )
    def update_footstep_thumbnail_src(thumbnail_revisions, thumbnail_id):
        if not thumbnail_id:
            raise PreventUpdate

        event_id = str(thumbnail_id["event_id"])
        footstep_id = int(thumbnail_id["footstep_id"])
        revisions = thumbnail_revisions or {}
        revision_key = _thumbnail_revision_key(event_id, footstep_id)

        if revision_key not in revisions:
            raise PreventUpdate

        return _footstep_thumbnail_src(
            event_id,
            footstep_id,
            thumbnail_revisions=revisions,
        )

    @callback(
        Output("footstep-review-store", "data", allow_duplicate=True),
        Input(
            {"type": "footstep-review-open", "event_id": ALL, "footstep_id": ALL},
            "n_clicks",
        ),
        Input("btn-close-footstep-review", "n_clicks"),
        prevent_initial_call=True,
    )
    def open_or_close_footstep_review(_open_clicks, _close_clicks):
        triggered = ctx.triggered_id

        if triggered == "btn-close-footstep-review":
            return _empty_review()

        if not isinstance(triggered, dict):
            raise PreventUpdate

        if triggered.get("type") != "footstep-review-open":
            raise PreventUpdate

        clicked_value = None
        if ctx.inputs_list and isinstance(ctx.inputs_list[0], list):
            for item in ctx.inputs_list[0]:
                if item.get("id") == triggered:
                    clicked_value = item.get("value")
                    break

        if clicked_value in (None, 0):
            raise PreventUpdate

        event_id = str(triggered["event_id"])
        footstep_id = int(triggered["footstep_id"])

        review = get_footstep_review(
            event_id,
            footstep_id,
            logger=app.logger,
        )

        return _open_review(
            event_id,
            footstep_id,
            review,
            "Drag the box or edit the numbers, then click Save.",
        )

    @callback(
        Output("footstep-review-panel", "style"),
        Output("footstep-review-title", "children"),
        Output("footstep-review-status", "children"),
        Output("footstep-create-start-frame", "value"),
        Output("footstep-create-end-frame", "value"),
        Output("footstep-review-x-min", "value"),
        Output("footstep-review-x-max", "value"),
        Output("footstep-review-y-min", "value"),
        Output("footstep-review-y-max", "value"),
        Output("footstep-review-label", "value"),
        Output("footstep-review-history", "children"),
        Output("btn-create-footstep", "children"),
        Output("btn-cancel-create-footstep", "style"),
        Output("btn-delete-footstep", "style"),
        Output("btn-save-footstep-review", "children"),
        Output("btn-save-footstep-review", "style"),
        Output("btn-show-footstep-history", "style"),
        Input("footstep-review-store", "data"),
        State("footstep-results-store", "data"),
        prevent_initial_call=False,
    )
    def populate_footstep_review_panel(review_store, visible_items):
        if (
            not review_store
            or not review_store.get("open")
            or not review_store.get("review")
        ):
            return (
                {"display": "flex", "flexDirection": "column"},
                "Review",
                "Click a footstep thumbnail to edit its bbox on the full event image.",
                None,
                None,
                None,
                None,
                None,
                None,
                "",
                "No local changes yet.",
                "Create New",
                {"display": "none"},
                {"display": "inline-block"},
                "Edit",
                {"display": "inline-block"},
                {"display": "inline-block"},
            )

        review = review_store["review"]
        item = review["item"]
        bbox = review["bbox"]
        create_mode = bool(review_store.get("create_mode"))
        step_number = _find_step_number(
            visible_items,
            event_id=str(item["event_id"]),
            footstep_id=int(item["footstep_id"]),
        )

        if create_mode:
            return (
                {"display": "flex", "flexDirection": "column"},
                f"{item['event_id']} · Create New Footstep",
                "Create mode is active. Adjust the bbox, click View Draft to preview, then click Create Footstep.",
                item["start_frame"],
                item["end_frame"],
                bbox["x_min"],
                bbox["x_max"],
                bbox["y_min"],
                bbox["y_max"],
                _review_label_value(item.get("label")),
                "Changelog is unavailable while create mode is active.",
                "View Draft",
                {"display": "inline-block"},
                {"display": "none"},
                "Create Footstep",
                {"display": "inline-block"},
                {"display": "none"},
            )

        return (
            {"display": "flex", "flexDirection": "column"},
            (
                f"{item['event_id']} · Step {step_number}"
                if step_number is not None
                else f"{item['event_id']} · Footstep"
            ),
            review_store.get("message")
            or "Drag the box or edit the numbers, then click Save.",
            item["start_frame"],
            item["end_frame"],
            bbox["x_min"],
            bbox["x_max"],
            bbox["y_min"],
            bbox["y_max"],
            _review_label_value(item.get("label")),
            _render_history(review.get("changes") or []),
            "Create New",
            {"display": "none"},
            {"display": "inline-block"},
            "Edit",
            {"display": "inline-block"},
            {"display": "inline-block"},
        )

    @callback(
        Output("footstep-context-title", "children"),
        Output("footstep-context-step", "children"),
        Output("footstep-context-meta", "children"),
        Output("footstep-context-p100-graph", "figure"),
        Output("footstep-context-grf-graph", "figure"),
        Input("footstep-context-store", "data"),
        State("footstep-results-store", "data"),
        prevent_initial_call=False,
    )
    def populate_footstep_context_panel(context_store, visible_items):
        if (
            not context_store
            or not context_store.get("open")
            or not context_store.get("details")
        ):
            return (
                "Footstep Context",
                "",
                "Click a thumbnail to inspect that footstep.",
                _placeholder_figure("No footstep selected.", height=260),
                _placeholder_figure("No GRF data to display yet.", height=220),
            )

        event_id = str(context_store["event_id"])
        footstep_id = int(context_store["footstep_id"])
        details = context_store["details"] or {}
        step_number = _find_step_number(
            visible_items,
            event_id=event_id,
            footstep_id=footstep_id,
        )

        return (
            "Footstep Context",
            f"Step {step_number}" if step_number is not None else "",
            f"Event ID: {event_id}\nBackend Footstep ID: {footstep_id}",
            _make_context_p100_figure(
                details.get("p100"),
                cmap,
                details.get("cop_x"),
                details.get("cop_y"),
            ),
            _make_context_grf_figure(details.get("grf")),
        )

    @callback(
        Output("footstep-history-modal", "style"),
        Input("btn-show-footstep-history", "n_clicks"),
        Input("btn-close-footstep-history", "n_clicks"),
        Input("footstep-review-store", "data"),
        State("footstep-history-modal", "style"),
        prevent_initial_call=False,
    )
    def toggle_footstep_history_modal(
        _show_clicks,
        _close_clicks,
        review_store,
        current_style,
    ):
        if (
            not review_store
            or not review_store.get("open")
            or not review_store.get("review")
            or review_store.get("create_mode")
        ):
            return {"display": "none"}

        triggered = ctx.triggered_id

        if triggered == "btn-show-footstep-history":
            return {"display": "flex"}

        if triggered == "btn-close-footstep-history":
            return {"display": "none"}

        if current_style and current_style.get("display") == "flex":
            return {"display": "flex"}

        return {"display": "none"}

    @callback(
        Output("footstep-delete-modal", "style"),
        Input("btn-delete-footstep", "n_clicks"),
        Input("btn-cancel-delete-footstep", "n_clicks"),
        Input("btn-confirm-delete-footstep", "n_clicks"),
        Input("footstep-review-store", "data"),
        State("footstep-delete-modal", "style"),
        prevent_initial_call=False,
    )
    def toggle_footstep_delete_modal(
        _open_clicks,
        _cancel_clicks,
        _confirm_clicks,
        review_store,
        current_style,
    ):
        if (
            not review_store
            or not review_store.get("open")
            or not review_store.get("review")
            or review_store.get("create_mode")
        ):
            return {"display": "none"}

        triggered = ctx.triggered_id

        if triggered == "btn-delete-footstep":
            return {"display": "flex"}

        if triggered == "btn-cancel-delete-footstep":
            return {"display": "none"}

        if triggered == "btn-confirm-delete-footstep":
            return {"display": "none"}

        if current_style and current_style.get("display") == "flex":
            return {"display": "flex"}

        return {"display": "none"}

    @callback(
        Output("footstep-review-graph", "figure"),
        Input("footstep-review-store", "data"),
        Input("footstep-review-x-min", "value"),
        Input("footstep-review-x-max", "value"),
        Input("footstep-review-y-min", "value"),
        Input("footstep-review-y-max", "value"),
        prevent_initial_call=False,
    )
    def draw_footstep_review_graph(review_store, x_min, x_max, y_min, y_max):
        if (
            not review_store
            or not review_store.get("open")
            or not review_store.get("review")
        ):
            fig = px.imshow(
                np.zeros((720, 480)),
                zmin=0,
                zmax=1,
                color_continuous_scale=cmap,
            )
            fig.update_layout(
                margin={"l": 10, "r": 10, "t": 10, "b": 10},
                coloraxis_showscale=False,
            )
            fig.update_xaxes(visible=False)
            fig.update_yaxes(visible=False)
            return fig

        review = review_store["review"]
        bbox = _get_bbox(
            review,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
        )
        return _make_figure(review, bbox, cmap)

    @callback(
        Output("footstep-review-x-min", "value", allow_duplicate=True),
        Output("footstep-review-x-max", "value", allow_duplicate=True),
        Output("footstep-review-y-min", "value", allow_duplicate=True),
        Output("footstep-review-y-max", "value", allow_duplicate=True),
        Input("footstep-review-graph", "relayoutData"),
        State("footstep-review-store", "data"),
        State("footstep-review-x-min", "value"),
        State("footstep-review-x-max", "value"),
        State("footstep-review-y-min", "value"),
        State("footstep-review-y-max", "value"),
        prevent_initial_call=True,
    )
    def sync_bbox_inputs_from_graph(
        relayout_data,
        review_store,
        x_min,
        x_max,
        y_min,
        y_max,
    ):
        if (
            not review_store
            or not review_store.get("open")
            or not review_store.get("review")
            or not relayout_data
        ):
            raise PreventUpdate

        review = review_store["review"]
        bbox = _get_bbox(
            review,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
        )

        if "shapes" in relayout_data and relayout_data["shapes"]:
            shape = relayout_data["shapes"][-1]
            return (
                int(
                    round(
                        min(
                            shape.get("x0", bbox["x_min"]),
                            shape.get("x1", bbox["x_max"]),
                        )
                    )
                ),
                int(
                    round(
                        max(
                            shape.get("x0", bbox["x_min"]),
                            shape.get("x1", bbox["x_max"]),
                        )
                    )
                ),
                int(
                    round(
                        min(
                            shape.get("y0", bbox["y_min"]),
                            shape.get("y1", bbox["y_max"]),
                        )
                    )
                ),
                int(
                    round(
                        max(
                            shape.get("y0", bbox["y_min"]),
                            shape.get("y1", bbox["y_max"]),
                        )
                    )
                ),
            )

        if (
            "shapes[0].x0" in relayout_data
            and "shapes[0].x1" in relayout_data
            and "shapes[0].y0" in relayout_data
            and "shapes[0].y1" in relayout_data
        ):
            x0 = relayout_data["shapes[0].x0"]
            x1 = relayout_data["shapes[0].x1"]
            y0 = relayout_data["shapes[0].y0"]
            y1 = relayout_data["shapes[0].y1"]

            return (
                int(round(min(x0, x1))),
                int(round(max(x0, x1))),
                int(round(min(y0, y1))),
                int(round(max(y0, y1))),
            )

        raise PreventUpdate

    @callback(
        Output("footstep-review-store", "data", allow_duplicate=True),
        Output("btn-apply-footstep-filters", "n_clicks", allow_duplicate=True),
        Input("btn-create-footstep", "n_clicks"),
        State("footstep-review-store", "data"),
        State("btn-apply-footstep-filters", "n_clicks"),
        State("footstep-create-start-frame", "value"),
        State("footstep-create-end-frame", "value"),
        State("footstep-review-x-min", "value"),
        State("footstep-review-x-max", "value"),
        State("footstep-review-y-min", "value"),
        State("footstep-review-y-max", "value"),
        State("footstep-review-label", "value"),
        prevent_initial_call=True,
    )
    def create_or_enter_create_mode(
        _n_clicks,
        review_store,
        ok_clicks,
        start_frame,
        end_frame,
        x_min,
        x_max,
        y_min,
        y_max,
        label,
    ):
        if (
            not review_store
            or not review_store.get("open")
            or not review_store.get("review")
        ):
            raise PreventUpdate

        if not review_store.get("create_mode"):
            return (
                {
                    **review_store,
                    "create_mode": True,
                    "message": "Create mode is active.",
                },
                no_update,
            )
        raise PreventUpdate

    @callback(
        Output("footstep-draft-store", "data"),
        Input("footstep-draft-request-store", "data"),
        prevent_initial_call=True,
    )
    def build_footstep_draft(request_data):
        if not request_data:
            raise PreventUpdate

        event_id = str(request_data["event_id"])
        x_min = int(request_data["x_min"])
        x_max = int(request_data["x_max"])
        y_min = int(request_data["y_min"])
        y_max = int(request_data["y_max"])

        return create_draft_footstep(
            event_id,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
            logger=app.logger,
        )

    @callback(
        Output("footstep-draft-range-slider", "min"),
        Output("footstep-draft-range-slider", "max"),
        Output("footstep-draft-range-slider", "value"),
        Output("footstep-draft-range-slider", "marks"),
        Output("footstep-draft-graph", "figure"),
        Output("footstep-draft-grf-graph", "figure"),
        Output("footstep-draft-info", "children"),
        Input("footstep-draft-store", "data"),
        Input("footstep-draft-range-slider", "value"),
        prevent_initial_call=False,
    )
    def populate_footstep_draft_preview(draft_store, depth_range):
        if not draft_store or not draft_store.get("volume"):
            return (
                0,
                0,
                [0, 0],
                {0: "0"},
                _make_draft_placeholder_figure("Loading draft preview..."),
                _placeholder_figure("GRF not available for this draft.", height=420),
                "Draft preview will appear here.",
            )

        volume = draft_store["volume"]
        depth = len(volume)
        draft_start = int(draft_store.get("start_frame", 0))
        draft_end = draft_start + max(0, depth - 1)
        resolved_range = _resolve_draft_frame_range(
            draft_start=draft_start,
            draft_end=draft_end,
            frame_range=depth_range,
            reset_range=ctx.triggered_id == "footstep-draft-store",
        )
        start_idx = resolved_range[0] - draft_start
        end_idx = resolved_range[1] - draft_start

        marks = {
            frame: str(frame)
            for frame in sorted(
                {draft_start, draft_end, (draft_start + draft_end) // 2}
            )
        }
        projected = _max_projection_in_range(volume, start_idx, end_idx)
        max_pressure = float(np.max(projected)) if projected is not None else 0.0

        return (
            draft_start,
            draft_end,
            resolved_range,
            marks,
            _make_draft_preview_figure(volume, [start_idx, end_idx], cmap),
            _make_draft_grf_figure(
                volume,
                resolved_range,
                draft_start_frame=draft_start,
            ),
            (
                f"Frame range: [{resolved_range[0]}, {resolved_range[1]}] | "
                f"Projected image shape: {np.asarray(projected).shape if projected is not None else 'N/A'} | "
                f"Max pressure in projection: {max_pressure:.3f}"
            ),
        )

    @callback(
        Output("footstep-create-start-frame", "value", allow_duplicate=True),
        Output("footstep-create-end-frame", "value", allow_duplicate=True),
        Input("footstep-draft-store", "data"),
        Input("footstep-draft-range-slider", "value"),
        prevent_initial_call=True,
    )
    def sync_draft_range_to_create_frames(draft_store, depth_range):
        frame_bounds = _draft_range_to_frame_bounds(draft_store, depth_range)
        if frame_bounds is None:
            raise PreventUpdate

        return frame_bounds

    @callback(
        Output("footstep-review-store", "data", allow_duplicate=True),
        Input("btn-cancel-create-footstep", "n_clicks"),
        State("footstep-review-store", "data"),
        prevent_initial_call=True,
    )
    def cancel_create_mode(_n_clicks, review_store):
        if (
            not review_store
            or not review_store.get("open")
            or not review_store.get("review")
            or not review_store.get("create_mode")
        ):
            raise PreventUpdate

        return {
            **review_store,
            "create_mode": False,
            "message": "Create mode cancelled.",
        }

    @callback(
        Output("footstep-review-store", "data", allow_duplicate=True),
        Output("footstep-pagination-store", "data", allow_duplicate=True),
        Output("footstep-results-store", "data", allow_duplicate=True),
        Output("footstep-thumbnail-revision-store", "data", allow_duplicate=True),
        Input("btn-confirm-delete-footstep", "n_clicks"),
        State("footstep-review-store", "data"),
        State("footstep-pagination-store", "data"),
        State("footstep-results-store", "data"),
        State("footstep-thumbnail-revision-store", "data"),
        prevent_initial_call=True,
    )
    def confirm_delete_footstep(
        _n_clicks,
        review_store,
        pagination_store,
        visible_items,
        thumbnail_revisions,
    ):
        if (
            not review_store
            or not review_store.get("open")
            or not review_store.get("review")
            or review_store.get("create_mode")
        ):
            raise PreventUpdate

        event_id = str(review_store["event_id"])
        footstep_id = int(review_store["footstep_id"])

        delete_footstep(
            event_id,
            footstep_id,
            logger=app.logger,
        )

        if not pagination_store or not pagination_store.get("applied"):
            return _empty_review(), no_update, no_update, no_update

        size_range = pagination_store.get("size_range", [0, 10000])
        height_range = pagination_store.get("height_range", [10, 150])
        width_range = pagination_store.get("width_range", [10, 130])
        visible_count = max(1, len(visible_items or []))

        refreshed_result = search_footsteps(
            event_ids=None,
            participants=pagination_store.get("participants") or None,
            date_from=pagination_store.get("start_date"),
            date_to=pagination_store.get("end_date"),
            width_min=int(width_range[0]),
            width_max=int(width_range[1]),
            height_min=int(height_range[0]),
            height_max=int(height_range[1]),
            size_min=int(size_range[0]),
            size_max=int(size_range[1]),
            offset=0,
            limit=visible_count,
            logger=app.logger,
        ) or {"items": [], "total": 0}

        refreshed_items = refreshed_result.get("items", [])
        refreshed_total = int(refreshed_result.get("total", 0))
        updated_thumbnail_revisions = _refresh_thumbnail_revisions_for_event(
            thumbnail_revisions,
            event_id=event_id,
            items=refreshed_items,
        )
        updated_pagination_store = {
            **pagination_store,
            "offset": len(refreshed_items),
            "total": refreshed_total,
        }

        return (
            _empty_review(),
            updated_pagination_store,
            refreshed_items,
            updated_thumbnail_revisions,
        )

    @callback(
        Output("footstep-thumbnail-revision-store", "data", allow_duplicate=True),
        Output("footstep-review-store", "data", allow_duplicate=True),
        Output("footstep-context-store", "data", allow_duplicate=True),
        Output("footstep-pagination-store", "data", allow_duplicate=True),
        Output("footstep-results-store", "data", allow_duplicate=True),
        Input("btn-save-footstep-review", "n_clicks"),
        State("footstep-review-store", "data"),
        State("footstep-review-x-min", "value"),
        State("footstep-review-x-max", "value"),
        State("footstep-review-y-min", "value"),
        State("footstep-review-y-max", "value"),
        State("footstep-create-start-frame", "value"),
        State("footstep-create-end-frame", "value"),
        State("footstep-review-label", "value"),
        State("footstep-thumbnail-revision-store", "data"),
        State("footstep-context-store", "data"),
        State("footstep-pagination-store", "data"),
        State("footstep-results-store", "data"),
        prevent_initial_call=True,
    )
    def save_current_footstep_review(
        _n_clicks,
        review_store,
        x_min,
        x_max,
        y_min,
        y_max,
        start_frame,
        end_frame,
        label,
        thumbnail_revisions,
        context_store,
        pagination_store,
        visible_items,
    ):
        if (
            not review_store
            or not review_store.get("open")
            or not review_store.get("review")
        ):
            raise PreventUpdate

        event_id = str(review_store["event_id"])
        review = review_store["review"]

        bbox = _get_bbox(
            review,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
        )

        new_thumbnail_revisions = dict(thumbnail_revisions or {})

        if review_store.get("create_mode"):
            if start_frame is None or end_frame is None:
                raise PreventUpdate

            created = create_footstep(
                event_id,
                start_frame=int(start_frame),
                end_frame=int(end_frame),
                x_min=bbox["x_min"],
                x_max=bbox["x_max"],
                y_min=bbox["y_min"],
                y_max=bbox["y_max"],
                label=label,
                logger=app.logger,
            )

            new_footstep_id = int(created["item"]["footstep_id"])
            refreshed_details = get_footstep_details(
                event_id,
                new_footstep_id,
                logger=app.logger,
            )
            refreshed_pagination_store, refreshed_items = (
                _refresh_visible_results_for_created_footstep(
                    pagination_store,
                    visible_items,
                    event_id=event_id,
                    footstep_id=new_footstep_id,
                    logger=app.logger,
                )
            )
            revision_key = _thumbnail_revision_key(event_id, new_footstep_id)
            new_thumbnail_revisions[revision_key] = (
                int(new_thumbnail_revisions.get(revision_key, 0)) + 1
            )

            return (
                new_thumbnail_revisions,
                _open_review(
                    event_id,
                    new_footstep_id,
                    created,
                    "Created new footstep locally.",
                ),
                {
                    **(context_store or _empty_context()),
                    "open": True,
                    "event_id": event_id,
                    "footstep_id": new_footstep_id,
                    "details": refreshed_details,
                },
                refreshed_pagination_store if refreshed_pagination_store else no_update,
                refreshed_items if refreshed_items is not None else no_update,
            )

        footstep_id = int(review_store["footstep_id"])
        saved = save_footstep_review(
            event_id,
            footstep_id,
            x_min=bbox["x_min"],
            x_max=bbox["x_max"],
            y_min=bbox["y_min"],
            y_max=bbox["y_max"],
            start_frame=start_frame,
            end_frame=end_frame,
            label=label,
            logger=app.logger,
        )
        refreshed_details = get_footstep_details(
            event_id,
            footstep_id,
            logger=app.logger,
        )
        revision_key = _thumbnail_revision_key(event_id, footstep_id)
        new_thumbnail_revisions[revision_key] = (
            int(new_thumbnail_revisions.get(revision_key, 0)) + 1
        )

        return (
            new_thumbnail_revisions,
            _open_review(
                event_id,
                footstep_id,
                saved,
                "Saved local bbox and label.",
            ),
            {
                **(context_store or _empty_context()),
                "open": True,
                "event_id": event_id,
                "footstep_id": footstep_id,
                "details": refreshed_details,
            },
            no_update,
            no_update,
        )
