from dash import html
from dash.dcc import Graph
import plotly.express as px


class SummaryView:
    def __init__(self, event_id, cmap):
        self.event_id = event_id
        self.cmap = cmap

    def render(self):
        dummy_data = [[0]]
        figure = px.imshow(dummy_data, color_continuous_scale=self.cmap)
        return html.Div(
            children=[
                html.H3(f"P100 for Event ID: {self.event_id}"),
                Graph(id="p100-graph", figure=figure),
            ],
            style={
                "height": "75vh",
                "maxWidth": "1500px",
                "flex": "1",
                "display": "flex",
                "justifyContent": "center",
            },
        )
