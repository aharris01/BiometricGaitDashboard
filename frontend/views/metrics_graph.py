from dash import html, dcc
from frontend.views.filters import ParticipantMultiSelect, DateSelector
import plotly.graph_objects as go


class MetricsGraph:
    def __init__(self, swipe_event_metrics=None):
        self.metrics = swipe_event_metrics or {}

    def _placeholder_figure(self, text, height=520):
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

    def render(self):
        # ---- Scatter plot (all swipe events summary) ----
        if self.metrics:
            event_ids = list(self.metrics.keys())
            x_vals = [self.metrics[e]["avg_box_size"] for e in event_ids]
            y_vals = [self.metrics[e]["footstep_count"] for e in event_ids]

            scatter_plot = go.Figure()
            scatter_plot.add_trace(
                go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode="markers",
                    text=event_ids,
                    hovertemplate="<b>Event:</b> %{text}<br>"
                    + "<b>Average Box Size:</b> %{x}<br>"
                    + "<b>Footstep Count:</b> %{y}"
                    + "<extra></extra>",
                )
            )
            scatter_plot.update_layout(
                xaxis_title="Average Bounding Box Size",
                yaxis_title="Footstep Count",
                margin=dict(l=30, r=20, t=20, b=40),
            )
        else:
            scatter_plot = self._placeholder_figure(
                "Summary scatter not available (no metrics data)."
            )

        # ---- UI-only demo options (replace with real data later) ----
        participant_options = [
            {"label": "100", "value": 100},
            {"label": "101", "value": 101},
            {"label": "102", "value": 102},
        ]

        figure_div = html.Div(
            className="metrics-row",
            children=[
                # 1) Filters panel (left)
                html.Div(
                    className="metrics-panel",
                    children=[
                        html.Div(
                            className="metrics-panel-scroll",
                            children=[
                                html.H4("Filters", className="metrics-title"),
                                ParticipantMultiSelect(
                                    id="metrics-filter-participant",
                                    options=participant_options,
                                ),
                                DateSelector(id="metrics-filter-date"),
                            ],
                        )
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
                            config={"displayModeBar": True},
                            style={"height": "520px"},
                        ),
                    ],
                ),

                # 3) Arrow buttons (middle)
                html.Div(
                    className="metrics-arrows",
                    children=[
                        html.Button("▶", id="btn-add-selected", className="arrow-btn"),
                        html.Button("◀", id="btn-remove-selected", className="arrow-btn"),
                    ],
                ),

                # 4) Selected list (right)
                html.Div(
                    className="metrics-panel",
                    children=[
                        html.Div(
                            className="metrics-panel-scroll",
                            children=[
                                html.H4("Selected", className="metrics-title"),
                                html.Div(
                                    id="metrics-selected-list",
                                    children="(selected items here)",
                                ),
                            ],
                        )
                    ],
                ),
            ],
        )

        return html.Div(
            children=[figure_div],
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
