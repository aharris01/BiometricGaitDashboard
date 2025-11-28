from dash import html
from dash.dcc import Graph
import plotly.express as px


class SummaryView:
    def __init__(self, event_id, cmap, p100_data):
        self.event_id = event_id
        self.cmap = cmap
        self.p100_data = p100_data or []

    def render(self):
        p100_figure = px.imshow(self.p100_data, color_continuous_scale=self.cmap)
        return html.Div(
            children=[
                html.H3(f"P100 for Event ID: {self.event_id}"),
                Graph(id="p100-graph", figure=p100_figure),
            ],
            style={
                "height": "75vh",
                "maxWidth": "1500px",
                "flex": "1",
                "display": "flex",
                "justifyContent": "center",
            },
        )
