from dash import html
from dash.dcc import Graph
import plotly.express as px  # type: ignore


class SummaryView:
    def __init__(self, event_id, data):
        self.event_id = event_id

    def render(self):
        return html.Div(
            children=[
                html.H3(f"Summary for Event ID: {self.event_id}"),
                Graph(
                    id="summary-graph",
                    figure={
                        "data": [
                            {
                                "x": [1, 2, 3],
                                "y": [4, 1, 2],
                                "type": "bar",
                                "name": "Sample Data",
                            }
                        ],
                        "layout": {"title": "Event Summary Graph"},
                    },
                ),
            ]
        )
