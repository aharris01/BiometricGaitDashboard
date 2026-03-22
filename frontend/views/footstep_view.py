# frontend/views/footstep_view.py

from dash import dcc, html

from frontend.api import API_BASE_URL


# -------------------------------------------------
# Small view helpers
# -------------------------------------------------


def render_footstep_empty(message: str):
    # Render a simple empty-state message for the footstep results panel.
    return [
        html.Div(
            message,
            className="footstep-empty",
        )
    ]


def _footstep_thumbnail_src(
    event_id: str,
    footstep_id: int,
    thumbnail_revisions: dict[str, int] | None = None,
) -> str:
    revisions = thumbnail_revisions or {}
    revision = int(revisions.get(f"{event_id}:{footstep_id}", 0))
    return (
        f"{API_BASE_URL}/api/events/{event_id}/footsteps/{footstep_id}/image"
        f"?rev={revision}"
    )


def render_footstep_cards(
    items: list[dict], thumbnail_revisions: dict[str, int] | None = None
):
    # Build one card per footstep search result.
    #
    # Each card shows:
    # - the event ID and step number
    # - a clickable thumbnail used to open the review editor
    # - the total bounding-box area
    cards = []

    for item in items:
        event_id = str(item["event_id"])
        footstep_id = int(item["footstep_id"])
        step_number = item.get("step_number")
        bbox_area = item.get("bbox_area")
        has_thumbnail = bool(item.get("has_thumbnail", True))

        cards.append(
            html.Div(
                className="footstep-card",
                children=[
                    html.Div(
                        (
                            f"{event_id} · Step {step_number}"
                            if step_number is not None
                            else f"{event_id} · Footstep"
                        ),
                        className="footstep-card-title",
                    ),
                    html.Button(
                        id={
                            "type": "footstep-review-open",
                            "event_id": event_id,
                            "footstep_id": footstep_id,
                        },
                        n_clicks=0,
                        className="footstep-card-image-button",
                        children=[
                            html.Img(
                                id={
                                    "type": "footstep-thumbnail",
                                    "event_id": event_id,
                                    "footstep_id": footstep_id,
                                },
                                src=_footstep_thumbnail_src(
                                    event_id,
                                    footstep_id,
                                    thumbnail_revisions=thumbnail_revisions,
                                ),
                                className="footstep-card-image",
                            )
                            if has_thumbnail
                            else html.Div(
                                "Placeholder",
                                className="footstep-card-placeholder",
                            )
                        ],
                    ),
                    html.Div(
                        f"Area: {int(bbox_area) if bbox_area is not None else 'N/A'}",
                        className="footstep-card-meta",
                    ),
                    html.Div(
                        "Click thumbnail to review on event image",
                        className="footstep-card-hint",
                    ),
                ],
            )
        )

    return cards


# -------------------------------------------------
# Footstep view layout
# -------------------------------------------------


def FootstepView():
    # This page is split into two full-height rows:
    # - top row: filters and footstep thumbnails
    # - bottom row: full-width review/editor panel
    #
    # The changelog opens in a modal so it does not steal width from the
    # review graph or the thumbnail grid.
    return html.Div(
        id="footstep-view",
        className="hidden",
        children=[
            html.Div(
                className="footstep-layout",
                children=[
                    html.Div(
                        className="footstep-row footstep-top-row",
                        children=[
                            # -------------------------------------------------
                            # Left sidebar: footstep filters
                            # -------------------------------------------------
                            html.Div(
                                className="footstep-sidebar",
                                children=[
                                    html.Div(
                                        className="panel-header",
                                        children=[
                                            html.H3("Filters", className="panel-title"),
                                            html.Div(
                                                className="footstep-filter-actions",
                                                children=[
                                                    html.Button(
                                                        "Clear",
                                                        id="btn-clear-footstep-filters",
                                                        className="mode-btn",
                                                    ),
                                                    html.Button(
                                                        "OK",
                                                        id="btn-apply-footstep-filters",
                                                        className="ok-btn",
                                                    ),
                                                ],
                                            )
                                        ],
                                    ),
                                    html.Details(
                                        open=False,
                                        children=[
                                            html.Summary(
                                                "by participant",
                                                className="filter_summary",
                                            ),
                                            html.Div(
                                                className="filter_box",
                                                children=[
                                                    dcc.Checklist(
                                                        id="footstep-participant-filter",
                                                        options=[],
                                                        value=[],
                                                        labelStyle={
                                                            "display": "block",
                                                            "marginBottom": "6px",
                                                        },
                                                    )
                                                ],
                                            ),
                                        ],
                                    ),
                                    html.Details(
                                        open=False,
                                        children=[
                                            html.Summary(
                                                "by date range",
                                                className="filter_summary",
                                            ),
                                            html.Div(
                                                className="filter_box_no_scroll",
                                                children=[
                                                    dcc.DatePickerRange(
                                                        id="footstep-date-range-filter",
                                                        start_date=None,
                                                        end_date=None,
                                                        minimum_nights=0,
                                                        display_format="YYYY-MM-DD",
                                                    )
                                                ],
                                            ),
                                        ],
                                    ),
                                    html.Details(
                                        open=False,
                                        children=[
                                            html.Summary(
                                                "by footstep size",
                                                className="filter_summary",
                                            ),
                                            html.Div(
                                                className="filter_box_no_scroll",
                                                children=[
                                                    html.Div(
                                                        className="metrics-field",
                                                        children=[
                                                            html.Label("Height"),
                                                            dcc.RangeSlider(
                                                                id="footstep-height-slider",
                                                                min=10,
                                                                max=150,
                                                                step=1,
                                                                value=[10, 150],
                                                                allowCross=False,
                                                                marks={
                                                                    10: "10",
                                                                    50: "50",
                                                                    100: "100",
                                                                    150: "150",
                                                                },
                                                            ),
                                                        ],
                                                    ),
                                                    html.Div(
                                                        className="metrics-field",
                                                        children=[
                                                            html.Label("Width"),
                                                            dcc.RangeSlider(
                                                                id="footstep-width-slider",
                                                                min=10,
                                                                max=130,
                                                                step=1,
                                                                value=[10, 130],
                                                                allowCross=False,
                                                                marks={
                                                                    10: "10",
                                                                    40: "40",
                                                                    80: "80",
                                                                    130: "130",
                                                                },
                                                            ),
                                                        ],
                                                    ),
                                                    html.Div(
                                                        className="metrics-field",
                                                        children=[
                                                            html.Label("Total Footstep Size"),
                                                            dcc.RangeSlider(
                                                                id="footstep-size-slider",
                                                                min=0,
                                                                max=10000,
                                                                step=50,
                                                                value=[0, 10000],
                                                                allowCross=False,
                                                                marks={
                                                                    0: "0",
                                                                    2500: "2.5k",
                                                                    5000: "5k",
                                                                    7500: "7.5k",
                                                                    10000: "10k",
                                                                },
                                                            ),
                                                        ],
                                                    ),
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            html.Div(
                                className="footstep-top-main",
                                children=[
                                    # -------------------------------------------------
                                    # Right panel: footstep search results
                                    # -------------------------------------------------
                                    html.Div(
                                        className="footstep-results-panel",
                                        children=[
                                            html.Div(
                                                className="panel-header",
                                                children=[
                                                    html.H3("Footsteps", className="panel-title"),
                                                    html.Div(
                                                        "Choose filters, then press OK.",
                                                        id="footstep-results-status",
                                                    ),
                                                ],
                                            ),
                                            html.Div(
                                                id="footstep-results-grid",
                                                className="footstep-card-grid",
                                                children=render_footstep_empty(
                                                    "No footsteps loaded yet. Choose filters and press OK."
                                                ),
                                            ),
                                            html.Div(
                                                id="footstep-load-more-wrap",
                                                style={"display": "none", "marginTop": "12px"},
                                                children=[
                                                    html.Button(
                                                        "Load More",
                                                        id="btn-load-more-footsteps",
                                                        className="mode-btn",
                                                    )
                                                ],
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        id="footstep-context-panel",
                                        className="footstep-context-panel",
                                        children=[
                                            html.Div(
                                                className="panel-header",
                                                children=[
                                                    html.H3(
                                                        "Footstep Context",
                                                        id="footstep-context-title",
                                                        className="panel-title",
                                                    ),
                                                ],
                                            ),
                                            html.Div(
                                                id="footstep-context-meta",
                                                className="footstep-context-meta",
                                                children="Click a thumbnail to inspect that footstep.",
                                            ),
                                            dcc.Graph(
                                                id="footstep-context-p100-graph",
                                                className="footstep-context-p100-graph",
                                                style={"height": "360px"},
                                                config={"displaylogo": False},
                                            ),
                                            dcc.Graph(
                                                id="footstep-context-grf-graph",
                                                className="footstep-context-grf-graph",
                                                style={"height": "220px"},
                                                config={"displaylogo": False},
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        className="footstep-row footstep-bottom-row",
                        children=[
                            html.Div(
                                id="footstep-review-panel",
                                className="footstep-review-panel",
                                style={"display": "none"},
                                children=[
                                    html.Div(
                                        className="panel-header",
                                        children=[
                                            html.H3(
                                                "Review",
                                                id="footstep-review-title",
                                                className="panel-title",
                                            ),
                                            html.Div(
                                                className="footstep-review-actions",
                                                children=[
                                                    html.Button(
                                                        "Create New",
                                                        id="btn-create-footstep",
                                                        className="mode-btn",
                                                    ),
                                                    html.Button(
                                                        "Cancel Create",
                                                        id="btn-cancel-create-footstep",
                                                        className="mode-btn",
                                                        style={"display": "none"},
                                                    ),
                                                    html.Button(
                                                        "Delete Footstep",
                                                        id="btn-delete-footstep",
                                                        className="mode-btn",
                                                    ),
                                                    html.Button(
                                                        "Show Changelog",
                                                        id="btn-show-footstep-history",
                                                        className="mode-btn",
                                                    ),
                                                    html.Button(
                                                        "Close",
                                                        id="btn-close-footstep-review",
                                                        className="mode-btn",
                                                    ),
                                                    html.Button(
                                                        "Save",
                                                        id="btn-save-footstep-review",
                                                        className="ok-btn",
                                                    ),
                                                ],
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        id="footstep-review-status",
                                        className="footstep-review-status",
                                        children="Click a footstep thumbnail to edit its bbox on the full event image.",
                                    ),
                                    html.Div(
                                        className="footstep-review-content",
                                        children=[
                                            html.Div(
                                                className="footstep-review-graph-wrap",
                                                children=[
                                                    dcc.Graph(
                                                        id="footstep-review-graph",
                                                        className="footstep-review-graph",
                                                        style={"height": "100%"},
                                                        config={
                                                            "displaylogo": False,
                                                            "modeBarButtonsToAdd": [
                                                                "drawrect",
                                                                "eraseshape",
                                                            ],
                                                            "edits": {"shapePosition": True},
                                                        },
                                                    )
                                                ],
                                            ),
                                            html.Div(
                                                className="footstep-review-fields",
                                                children=[
                                                    html.Div(
                                                        className="metrics-field",
                                                        children=[
                                                            html.Label("start_frame"),
                                                            dcc.Input(
                                                                id="footstep-create-start-frame",
                                                                type="number",
                                                                debounce=True,
                                                            ),
                                                        ],
                                                    ),
                                                    html.Div(
                                                        className="metrics-field",
                                                        children=[
                                                            html.Label("end_frame"),
                                                            dcc.Input(
                                                                id="footstep-create-end-frame",
                                                                type="number",
                                                                debounce=True,
                                                            ),
                                                        ],
                                                    ),
                                                    html.Div(
                                                        className="metrics-field",
                                                        children=[
                                                            html.Label("x_min"),
                                                            dcc.Input(
                                                                id="footstep-review-x-min",
                                                                type="number",
                                                                debounce=True,
                                                            ),
                                                        ],
                                                    ),
                                                    html.Div(
                                                        className="metrics-field",
                                                        children=[
                                                            html.Label("x_max"),
                                                            dcc.Input(
                                                                id="footstep-review-x-max",
                                                                type="number",
                                                                debounce=True,
                                                            ),
                                                        ],
                                                    ),
                                                    html.Div(
                                                        className="metrics-field",
                                                        children=[
                                                            html.Label("y_min"),
                                                            dcc.Input(
                                                                id="footstep-review-y-min",
                                                                type="number",
                                                                debounce=True,
                                                            ),
                                                        ],
                                                    ),
                                                    html.Div(
                                                        className="metrics-field",
                                                        children=[
                                                            html.Label("y_max"),
                                                            dcc.Input(
                                                                id="footstep-review-y-max",
                                                                type="number",
                                                                debounce=True,
                                                            ),
                                                        ],
                                                    ),
                                                    html.Div(
                                                        className="metrics-field",
                                                        children=[
                                                            html.Label("Label"),
                                                            dcc.Input(
                                                                id="footstep-review-label",
                                                                type="text",
                                                                debounce=True,
                                                            ),
                                                        ],
                                                    ),
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            # -------------------------------------------------
            # Changelog modal
            # -------------------------------------------------
            html.Div(
                id="footstep-history-modal",
                className="footstep-history-modal",
                style={"display": "none"},
                children=[
                    html.Div(
                        className="footstep-history-modal-card",
                        children=[
                            html.Div(
                                className="panel-header",
                                children=[
                                    html.H3(
                                        "Local Change History", className="panel-title"
                                    ),
                                    html.Button(
                                        "Close",
                                        id="btn-close-footstep-history",
                                        className="mode-btn",
                                    ),
                                ],
                            ),
                            html.Div(
                                id="footstep-review-history",
                                className="footstep-review-history",
                                children="No local changes yet.",
                            ),
                        ],
                    )
                ],
            ),
            html.Div(
                id="footstep-delete-modal",
                className="footstep-history-modal",
                style={"display": "none"},
                children=[
                    html.Div(
                        className="footstep-history-modal-card",
                        children=[
                            html.H3("Delete local footstep?", className="panel-title"),
                            html.Div(
                                "This will delete the footstep from your dataset files and the local database",
                                style={"marginBottom": "12px"},
                            ),
                            html.Div(
                                className="footstep-review-actions",
                                children=[
                                    html.Button(
                                        "Cancel",
                                        id="btn-cancel-delete-footstep",
                                        className="mode-btn",
                                    ),
                                    html.Button(
                                        "Delete",
                                        id="btn-confirm-delete-footstep",
                                        className="ok-btn",
                                    ),
                                ],
                            ),
                        ],
                    )
                ],
            ),
        ],
    )
