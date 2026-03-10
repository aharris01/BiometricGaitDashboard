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


def render_footstep_cards(items: list[dict]):
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
        bbox_area = item.get("bbox_area")

        cards.append(
            html.Div(
                className="footstep-card",
                children=[
                    html.Div(
                        f"{event_id} · Step {footstep_id}",
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
                                src=f"{API_BASE_URL}/api/events/{event_id}/footsteps/{footstep_id}/image",
                                className="footstep-card-image",
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
    # This page is split into three main parts:
    # - a filter sidebar on the left
    # - a results panel in the middle
    # - a review/edit panel on the right
    return html.Div(
        id="footstep-view",
        className="hidden",
        children=[
            html.Div(
                className="footstep-row",
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
                                    ),
                                ],
                            ),
                            # Filter by participant
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
                            # Filter by date range
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
                            # Filter by footstep size measurements
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
                                            # Bounding-box height range
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
                                            # Bounding-box width range
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
                                            # Total bounding-box area range
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
                    # -------------------------------------------------
                    # Middle panel: footstep search results
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
                    # -------------------------------------------------
                    # Right panel: full-event review/editor
                    # -------------------------------------------------
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
                            dcc.Graph(
                                id="footstep-review-graph",
                                style={"height": "850px"},
                                config={
                                    "displaylogo": False,
                                    "modeBarButtonsToAdd": [
                                        "drawrect",
                                        "eraseshape",
                                    ],
                                    "edits": {"shapePosition": True},
                                },
                            ),
                            html.Div(
                                className="footstep-review-fields",
                                children=[
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
            )
        ],
    )
