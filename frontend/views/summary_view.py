from dash import html
from dash.dcc import Graph
import plotly.express as px


class SummaryView:
    def __init__(self, event_id, cmap, p100_data, grf_data=None):
        self.event_id = event_id
        self.cmap = cmap
        self.p100_data = p100_data or []
        self.grf_data = grf_data or []

    def render(self):
        # ---- P100 heatmap ----
        p100_figure = px.imshow(self.p100_data, color_continuous_scale=self.cmap)

        # Make P100 bigger and pull colourbar closer
        p100_figure.update_layout(
            height=500,               # taller
            width=500,                # wider
            margin=dict(l=20, r=40, t=20, b=40),
            coloraxis_colorbar=dict(
                thickness=20,        # slim colour bar
                xpad=5,              # small gap between image and colour bar
            ),
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
                style={"marginBottom": "16px"},
            ),

            # P100 plot
            Graph(
                id="p100-graph",
                figure=p100_figure,
                style={
                    "maxWidth": "700px",   # allow space for colourbar
                    "height": "520px",
                },
            ),
        ]

        # Spacer then GRF plot (if we have data)
        components.append(html.Div(style={"height": "32px"}))

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
