from __future__ import annotations
from dash import html, dcc, callback, Output, Input
from dash.exceptions import PreventUpdate
from frontend.views.filters import collapsible_checklist
from frontend.utils import with_select_all
from frontend.api import get_participants

import json
import plotly.graph_objects as go


class MetricsGraph:
    def __init__(self, swipe_event_metrics: dict | None = None):
        self.metrics = swipe_event_metrics or {}

    def _placeholder_figure(self, text: str, height: int = 520) -> go.Figure:
        fig = go.Figure()
        fig.update_layout(
            height=height,
            xaxis={"visible": False},
            yaxis={"visible": False},
            plot_bgcolor="#e9f0fa",
            paper_bgcolor="#e9f0fa",
            margin=dict(l=0, r=0, t=0, b=0),
            annotations=[
                dict(
                    text=text,
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(color="#223a5e", size=14),
                )
            ],
        )
        return fig

    def get_swipe_event_id_on_click(self, event_id):
        print("Scatter plot click: " + event_id)

    def _build_scatter(self) -> go.Figure:
        if not self.metrics:
            return self._placeholder_figure(
                "Summary scatter not available (no metrics data)."
            )

        event_ids = list(self.metrics.keys())
        x_vals = [self.metrics[e]["avg_box_size"] for e in event_ids]
        y_vals = [self.metrics[e]["footstep_count"] for e in event_ids]

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="markers",
                text=event_ids,
                hovertemplate=(
                    "<b>Event:</b> %{text}<br>"
                    + "<b>Average Box Size:</b> %{x}<br>"
                    + "<b>Footstep Count:</b> %{y}"
                    + "<extra></extra>"
                ),
            )
        )
        fig.update_layout(
            xaxis_title="Average Bounding Box Size",
            yaxis_title="Footstep Count",
            margin=dict(l=30, r=20, t=20, b=40),
        )

        return fig

    @callback(
        Output("metrics-graph-click-data", "children"),
        Output("event-id-store", "data", allow_duplicate=True),
        Input("box-size-scatter-plot", "clickData"),
        prevent_initial_call=True,
    )
    def on_click_display_event_id(self):
        if self is None:
            raise PreventUpdate
        # Data point click logging
        print(self)

        click_data_json = json.dumps(self)
        click_data = json.loads(click_data_json)
        if click_data is not None:
            event_id = click_data["points"][0]["text"]
            return [self, {"event_id": event_id}]

    def render(self):
        scatter_plot = self._build_scatter()

        try:
            participant_options = with_select_all(get_participants(logger=None))
        except PreventUpdate:
            # tests / offline mode: no backend available
            participant_options = with_select_all([])


        return html.Div(
            children=[
                html.Div(
                    className="metrics-row",
                    children=[
                        # 1) Filters panel (left)
                        html.Div(
                            className="metrics-panel metrics-panel--filters",
                            children=[
                                dcc.Store(id="metrics_filter_participant_open_store", data=True, storage_type="session"),
                                # Header row
                                html.Div(
                                    className="panel-header",
                                    children=[
                                        html.H3("Filters", className="panel-title"),
                                        html.Button(
                                            "OK",
                                            id="btn-apply-filters",
                                            className="ok-btn",
                                        ),
                                    ],
                                ),

                                # Collapsible participant filter                                
                                collapsible_checklist(
                                    title="by participant",
                                    component_id="metrics_filter_participant",
                                    options=participant_options,
                                    open=True,
                                    details_id="metrics_filter_participant_details",
                                    summary_id="metrics_filter_participant_summary",
                                ),

                            ],
                        ),

                        # 2) Scatter plot (center)
                        html.Div(
                            className="metrics-plot",
                            children=[
                                html.H3(
                                    "Bounding box size scatter plot",
                                    style={"marginBottom": "6px", "marginTop": "4px"},
                                ),
                                dcc.Graph(
                                    id="box-size-scatter-plot",
                                    figure=scatter_plot,
                                    config={
                                        "displayModeBar": True,
                                        "modeBarButtonsToAdd": ["select2d", "lasso2d"],
                                    },
                                    style={"height": "520px"},
                                ),
                            ],
                        ),
                        # 3) Arrow buttons (middle)
                        html.Div(
                            className="metrics-arrows",
                            children=[
                                html.Button(
                                    "▶", id="btn-add-selected", className="arrow-btn"
                                ),
                                html.Button(
                                    "◀", id="btn-remove-selected", className="arrow-btn"
                                ),
                            ],
                        ),
                        # 4) Selected list (right)
                        html.Div(
                            className="metrics-panel metrics-panel--selected",
                            children=[
                                html.Div(
                                    className="panel-header",
                                    children=[
                                        html.H3("Selected", className="panel-title"),
                                        html.Button(
                                            "Select",
                                            id="btn-selected-select-mode",
                                            className="ok-btn",   # reuse same style as OK
                                        ),

                                    ],
                                ),
                                html.Div(
                                    className="metrics-panel-scroll",
                                    children=[
                                        html.Div(
                                            id="metrics-selected-list",
                                            children="(selected items here)",
                                        )
                                    ],
                                ),
                            ],
                        ),
                    ],
                )
            ],
            style={
                "width": "100%",
                "maxWidth": "1100px",
                "display": "flex",
                "flexDirection": "column",
                "alignItems": "flex-start",
                "margin": "0 auto",
                "paddingBottom": "16px",
            },
        )
