from dash import html
from dash.dcc import Graph
import plotly.express as px
import plotly.graph_objects as go


class SummaryView:
    def __init__(self, event_id, cmap, p100_data, grf_data=None):
        self.event_id = event_id
        self.cmap = cmap
        self.p100_data = p100_data or []
        self.grf_data = grf_data or []

    def render(self):
        # ---- P100 heatmap ----
        if self.p100_data:
            p100_figure = px.imshow(self.p100_data, color_continuous_scale=self.cmap)
            p100_figure.update_layout(
                height=520,
                width=480,
                margin=dict(l=20, r=10, t=10, b=40),
                coloraxis_colorbar=dict(
                    thickness=18,
                    xpad=0,
                ),
            )
        else:
            # Fallback empty figure if no P100 data
            p100_figure = go.Figure()
            p100_figure.update_layout(
                height=520,
                width=480,
                xaxis={"visible": False},
                yaxis={"visible": False},
                annotations=[
                    dict(
                        text="P100 not available for this event.",
                        x=0.5,
                        y=0.5,
                        xref="paper",
                        yref="paper",
                        showarrow=False,
                    )
                ],
            )

        # ---- GRF line plot (simple 1D case) ----
        grf_figure = None
        if self.grf_data:
            y = self.grf_data
            x = list(range(len(y)))
            grf_figure = px.line(
                x=x,
                y=y,
                labels={"x": "Frame", "y": "Force"},
                title="Ground Reaction Force (GRF)",
            )

        components = [
            html.H3(
                f"P100 for Event ID: {self.event_id}",
                style={"marginBottom": "4px", "marginTop": "8px"},
            ),
            Graph(
                id="p100-graph",
                figure=p100_figure,
                style={
                    "maxWidth": "700px",  # allow space for colourbar
                    "height": "520px",
                },
            ),
        ]

        # Spacer then GRF plot (if we have data)
        components.append(html.Div(style={"height": "16px"}))

        if grf_figure is not None:
            components.append(
                Graph(
                    id="grf-graph",
                    figure=grf_figure,
                    style={
                        "maxWidth": "900px",
                        "height": "300px",
                    },
                )
            )
        else:
            components.append(
                html.Div(
                    "GRF not available for this event.",
                    style={"fontStyle": "italic"},
                )
            )

        return html.Div(
            children=components,
            style={
                "width": "100%",
                "maxWidth": "900px",
                "display": "flex",
                "flexDirection": "column",
                "alignItems": "flex-start",  # left-align contents
                "margin": "0 auto",
                "paddingBottom": "32px",
            },
        )
