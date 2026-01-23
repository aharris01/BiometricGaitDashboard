from dash import html
from dash.dcc import Graph
from random import randrange
import plotly.graph_objects as go


class MetricsGraph:
    def __init__(self, metrics=None):
        self.metrics = metrics or {}

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
        # ---- Scatter plot ----
        if self.metrics:
            event_ids = list(self.metrics.keys())
            x_vals = [self.metrics[e]["avg_box_size"] for e in event_ids]
            y_vals = [self.metrics[e]["footstep_count"] for e in event_ids]

            scatter_plot = go.Figure()
            scatter_plot.add_trace(
                go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode="markers",  # only show data points (no connecting lines),
                    text=event_ids,
                    hovertemplate="<b>Event:</b> %{text}<br>"
                    + "<b>Average Box Size:</b> %{x}<br>"
                    + "<b>Footstep Count:</b> %{y}"
                    + "<extra></extra>",
                )
            )
            scatter_plot.update_layout(
                xaxis_title="Average Bounding Box Size", yaxis_title="Footstep Count"
            )
        else:
            scatter_plot = self._placeholder_figure(
                "Box size scatter not available for this event."
            )

        figure_div = html.Div(
            style={
                "display": "flex",
                "flexDirection": "row",
                "justifyContent": "space-between",
                "alignItems": "flex-start",
                "gap": "8px",
                "width": "100%",
            },
            children=[
                html.Div(
                    children=[
                        html.H3(
                            "Bounding box size scatter plot",
                            style={"marginBottom": "4px", "marginTop": "4px"},
                        ),
                        Graph(
                            id="box-size-scatter-plot",
                            figure=scatter_plot,
                            style={
                                "maxWidth": "2200px",
                                "maxHeight": "1000px",
                                "height": "700px",
                            },
                        ),
                    ],
                    style={"flex": "1"},
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
