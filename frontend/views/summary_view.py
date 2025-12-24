# frontend/views/summary_view.py
from dash import html
from dash.dcc import Graph
import plotly.express as px
import plotly.graph_objects as go


class SummaryView:
    def __init__(self, event_id, cmap, p100_data, grf_data=None, footsteps=None, *, step_p100s=None):
        self.event_id = event_id
        self.cmap = cmap
        self.p100_data = p100_data or []
        self.grf_data = grf_data or []
        self.footsteps = footsteps or []
        self.step_p100s = step_p100s or []

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

    def _bbox_shapes(self):
        shapes = []
        for box in self.footsteps:
            shapes.append(
                dict(
                    type="rect",
                    x0=box["x_min"],
                    x1=box["x_max"],
                    y0=box["y_min"],
                    y1=box["y_max"],
                    line=dict(color="rgba(255,0,255,0.9)", width=2),
                    fillcolor="rgba(0,0,0,0)",
                )
            )
        return shapes

    def _bbox_annotations(self):
        annotations = []
        for box in self.footsteps:
            width = box["x_max"] - box["x_min"]
            height = box["y_max"] - box["y_min"]
            area = int(width * height)
            annotations.append(
                dict(
                    x=box["x_min"],
                    y=box["y_min"],
                    text=f'#{box["id"]} ({area})',
                    showarrow=False,
                    xanchor="left",
                    yanchor="bottom",
                    font=dict(size=10, color="magenta"),
                    bgcolor="rgba(255,255,255,0.7)",
                )
            )
        return annotations

    def _render_all_step_grid(self):
        if not self.step_p100s:
            return html.Div(
                "No extracted footsteps available for this event.",
                style={"fontStyle": "italic", "marginTop": "8px"},
            )

        cards = []
        for item in self.step_p100s:
            step_id = item.get("id")
            step_p100 = item.get("p100", [])

            if step_p100:
                fig = px.imshow(step_p100, color_continuous_scale=self.cmap)
                fig.update_layout(
                    margin=dict(l=10, r=10, t=10, b=10),
                    coloraxis_showscale=False,
                    height=240,
                )
                fig.update_xaxes(visible=False)
                fig.update_yaxes(visible=False, autorange="reversed")
            else:
                fig = self._placeholder_figure("Step P100 not available.", height=240)

            cards.append(
                html.Div(
                    children=[
                        html.Div(
                            f"Footstep #{step_id}",
                            style={"fontWeight": "600", "marginBottom": "6px"},
                        ),
                        Graph(
                            id={"type": "step-p100", "step_id": step_id},
                            figure=fig,
                            # clickable thumbnails
                            config={"displayModeBar": False},
                            style={"height": "240px", "cursor": "pointer"},
                        ),
                    ],
                    style={
                        "border": "1px solid #e0e0e0",
                        "borderRadius": "8px",
                        "padding": "8px",
                        "background": "white",
                    },
                )
            )

        return html.Div(
            children=cards,
            style={
                "display": "grid",
                "gridTemplateColumns": "1fr 1fr",
                "gap": "12px",
            },
        )

    def render(self):
        # ---- P100 heatmap (full trial) ----
        if self.p100_data:
            p100_figure = px.imshow(self.p100_data, color_continuous_scale=self.cmap)
            p100_figure.update_layout(
                height=520,
                width=480,
                margin=dict(l=20, r=10, t=10, b=40),
                coloraxis_colorbar=dict(thickness=18, xpad=0),
                shapes=self._bbox_shapes(),
                annotations=self._bbox_annotations(),
            )
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
            grf_figure.add_trace(go.Scatter(x=x, y=y, mode="lines", name="GRF"))
            grf_figure.update_layout(
                title="Ground Reaction Force (GRF)",
                xaxis_title="Frame",
                yaxis_title="Force",
            )

        # Top row: full P100 | all steps grid (scrollable)
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
                            style={"maxWidth": "700px", "height": "520px"},
                        ),
                    ],
                    style={"flex": "1"},
                ),
                html.Div(
                    children=[
                        html.H4(
                            "All Footsteps (P100)",
                            style={"marginBottom": "8px", "marginTop": "24px"},
                        ),
                        html.Div(
                            children=self._render_all_step_grid(),
                            style={
                                "maxHeight": "560px",
                                "overflowY": "auto",
                                "paddingRight": "6px",
                            },
                        ),
                    ],
                    style={"flex": "1"},
                ),
            ],
        )

        # Bottom row: full GRF
        if grf_figure is not None:
            left_grf = Graph(
                id="grf-graph",
                figure=grf_figure,
                style={"maxWidth": "900px", "height": "300px"},
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
                        html.H3("Ground Reaction Force (GRF)", style={"marginBottom": "4px"}),
                        left_grf,
                    ],
                    style={"flex": "1"},
                ),
            ],
        )

        return html.Div(
            children=[top_row, bottom_row],
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
