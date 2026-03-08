# frontend/views/footstep_view.py

from dash import dcc, html

from frontend.api import API_BASE_URL


def render_footstep_empty(message: str):
    return [
        html.Div(
            message,
            className="footstep-empty",
        )
    ]


def render_footstep_cards(items: list[dict]):
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
                    html.Img(
                        src=f"{API_BASE_URL}/api/events/{event_id}/footsteps/{footstep_id}/image",
                        className="footstep-card-image",
                    ),
                    html.Div(
                        f"Area: {int(bbox_area) if bbox_area is not None else 'N/A'}",
                        className="footstep-card-meta",
                    ),
                ],
            )
        )

    return cards


def FootstepView():
    return html.Div(
        id="footstep-view",
        className="hidden",
        children=[
            html.Div(
                className="footstep-row",
                children=[
                    html.Div(
                        className="footstep-sidebar",
                        children=[
                            html.Div(
                                className="panel-header",
                                children=[
                                    html.H3("Filters", className="panel-title"),
                                ],
                            ),
                            html.Div(
                                className="metrics-field",
                                children=[
                                    html.Label("Bounding Box Area"),
                                    dcc.RangeSlider(
                                        id="footstep-size-slider",
                                        min=0,
                                        max=30000,
                                        step=50,
                                        value=[0, 30000],
                                        allowCross=False,
                                        marks={
                                            0: "0",
                                            10000: "10k",
                                            20000: "20k",
                                            30000: "30k",
                                        },
                                    ),
                                ],
                            ),
                            html.Button(
                                "Apply",
                                id="btn-apply-footstep-filters",
                                className="ok-btn",
                            ),
                        ],
                    ),
                    html.Div(
                        className="footstep-results-panel",
                        children=[
                            html.Div(
                                className="panel-header",
                                children=[
                                    html.H3("Footsteps", className="panel-title"),
                                    html.Div(
                                        "Choose filters, then press Apply.",
                                        id="footstep-results-status",
                                    ),
                                ],
                            ),
                            html.Div(
                                id="footstep-results-grid",
                                className="footstep-card-grid",
                                children=render_footstep_empty(
                                    "No footsteps loaded yet. Choose a size range and press Apply."
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
                ],
            )
        ],
    )
