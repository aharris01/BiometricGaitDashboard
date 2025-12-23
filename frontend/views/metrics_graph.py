from dash import html
from dash.dcc import Graph
from random import randrange
import plotly.graph_objects as go


class MetricsGraph:
    def __init__(self, event_id, footsteps=None):
        self.event_id = event_id
        self.footsteps = footsteps or []

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
        if self.footsteps:
            sum_box_size_for_avg = 0
            box_sizes = []  # list of bounding box (bbox) size of each footstep
            for footstep in self.footsteps:
                box_x = abs(footstep["x_max"] - footstep["x_min"])
                box_y = abs(footstep["y_max"] - footstep["y_min"])
                box_size = box_x * box_y
                box_sizes.append(box_size)
                sum_box_size_for_avg += box_size
            random_count = []
            for _box in box_sizes:
                random_count.append(randrange(1, 11, 1))

            scatter_plot = go.Figure()
            scatter_plot.add_trace(
                go.Scatter(
                    x=box_sizes,
                    y=random_count,
                    name="Box sizes",
                    mode="markers",  # only show data points (no connecting lines)
                )
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
                                "maxWidth": "1100px",
                                "width": "500px",
                                "height": "400px",
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
