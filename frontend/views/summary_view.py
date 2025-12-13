from dash import html
from dash.dcc import Graph
from random import randrange
import plotly.express as px
import plotly.graph_objects as go


class SummaryView:
    def __init__(self, event_id, cmap, p100_data, grf_data=None, footsteps=None):
        self.event_id = event_id
        self.cmap = cmap
        self.p100_data = p100_data or []
        self.grf_data = grf_data or []
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
        # ---- P100 heatmap (full trial) ----
        if self.p100_data:
            p100_figure = px.imshow(self.p100_data, color_continuous_scale=self.cmap)
            p100_figure.update_layout(
                height=520,
                width=480,
                margin=dict(l=20, r=10, t=10, b=40),
                coloraxis_colorbar=dict(thickness=18, xpad=0),
            )
            # keep pixels square
            p100_figure.update_xaxes(constrain="domain", scaleanchor="y")
            p100_figure.update_yaxes(autorange="reversed", constrain="domain")
        else:
            p100_figure = self._placeholder_figure("P100 not available for this event.")

        # ---- GRF line plot (full trial) ----
        grf_figure = None
        if self.grf_data:
            y = self.grf_data
            x = list(range(len(y)))

            grf_figure = go.Figure()
            grf_figure.add_trace(
                go.Scatter(
                    x=x,
                    y=y,
                    mode="lines",
                    name="GRF",
                )
            )
            grf_figure.update_layout(
                title="Ground Reaction Force (GRF)",
                xaxis_title="Frame",
                yaxis_title="Force",
            )

        # ---- Scatter plot ----
        if self.footsteps:
            sum_box_size = 0
            box_sizes = []
            for footstep in self.footsteps:
                box_x = abs(footstep["x_max"] - footstep["x_min"])
                box_y = abs(footstep["y_max"] - footstep["y_min"])
                box_size = box_x * box_y
                box_sizes.append(box_size)
                sum_box_size += box_size
            random_count = []
            for _box in box_sizes:
                random_count.append(randrange(1,11,1))
            y = random_count
            x = box_sizes

            scatter_plot = go.Figure()
            scatter_plot.add_trace(
                go.Scatter(
                    x=x,
                    y=y,
                    name="Box sizes",
                    mode="markers"
                )
            )
        else:
            scatter_plot = self._placeholder_figure("Box size scatter not available for this event.")

        # ---- Layout: 2x3 grid ----
        # Above top row: box size scatter_plot
        above_top_row = html.Div(
            style={
                "display": "flex",
                "flexDirection": "row",
                "justifyContent": "space-between",
                "alignItems": "flex-start",
                "gap": "32px",
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
                                "maxWidth": "700px",
                                "height": "400px",
                            },
                        ),
                    ],
                    style={"flex": "1"},
                ),
            ],
        )
        # Top row: full P100 | selected step P100
        top_row = html.Div(
            style={
                "display": "flex",
                "flexDirection": "row",
                "justifyContent": "space-between",
                "alignItems": "flex-start",
                "gap": "32px",
                "width": "100%",
            },
            children=[
                html.Div(
                    children=[
                        html.H3(
                            f"P100 for Event ID: {self.event_id}",
                            style={"marginBottom": "4px", "marginTop": "8px"},
                        ),
                        Graph(
                            id="p100-graph",
                            figure=p100_figure,
                            style={
                                "maxWidth": "700px",
                                "height": "520px",
                            },
                        ),
                    ],
                    style={"flex": "1"},
                ),
                html.Div(
                    children=[
                        html.H4(
                            "Selected Footstep (P100)",
                            style={"marginBottom": "4px", "marginTop": "24px"},
                        ),
                        Graph(
                            id="selected-p100-graph",
                            figure=self._placeholder_figure(
                                "Click a footstep in the P100 to see its step image here."
                            ),
                            style={"height": "520px"},
                        ),
                    ],
                    style={"flex": "1"},
                ),
            ],
        )

        # Bottom row: full GRF | selected step GRF
        if grf_figure is not None:
            left_grf = Graph(
                id="grf-graph",
                figure=grf_figure,
                style={
                    "maxWidth": "900px",
                    "height": "300px",
                },
            )
        else:
            left_grf = html.Div(
                "GRF not available for this event.",
                style={"fontStyle": "italic", "marginTop": "16px"},
            )

        bottom_row = html.Div(
            style={
                "display": "flex",
                "flexDirection": "row",
                "justifyContent": "space-between",
                "alignItems": "flex-start",
                "gap": "32px",
                "width": "100%",
                "marginTop": "24px",
            },
            children=[
                html.Div(
                    children=[
                        html.H3(
                            "Ground Reaction Force (GRF)",
                            style={"marginBottom": "4px"},
                        ),
                        left_grf,
                    ],
                    style={"flex": "1"},
                ),
                html.Div(
                    children=[
                        html.H4(
                            "Selected Footstep GRF",
                            style={"marginBottom": "4px", "marginTop": "24px"},
                        ),
                        Graph(
                            id="selected-grf-graph",
                            figure=self._placeholder_figure(
                                "Click a footstep in the P100 to see its GRF here.",
                                height=300,
                            ),
                            style={"height": "300px"},
                        ),
                    ],
                    style={"flex": "1"},
                ),
            ],
        )

        return html.Div(
            children=[above_top_row, top_row, bottom_row],
            style={
                "width": "100%",
                "maxWidth": "1100px",
                "display": "flex",
                "flexDirection": "column",
                "alignItems": "flex-start",
                "margin": "0 auto",
                "paddingBottom": "32px",
            },
        )
