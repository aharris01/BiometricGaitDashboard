from dash import html
from dash.dcc import Graph


class SummaryView:
    def __init__(self, event_id):
        self.event_id = event_id

    def render(self):
        return html.Div(
            children=[
                html.H3(f"P100 for Event ID: {self.event_id}"),
                Graph(
                    id="summary-graph",
                ),
            ]
        )
