from dash import Dash, Input, Output, State, callback
from dash.dcc import Dropdown, Interval
from dash.html import Div
import asyncio
import requests

API_BASE = "http://127.0.0.1:8000"

app = Dash(__name__)


app.layout = Div(
    [Dropdown(id="participant-dropdown"), Interval(id="page-load", max_intervals=1)]
)


@callback(Output("participant-dropdown", "options"), Input("page-load", "n_intervals"))
def getParticipants(_):
    resp = requests.get(f"{API_BASE}/api/participants", timeout=5)
    resp.raise_for_status()
    data = resp.json()
    return [{"label": str(p), "value": p} for p in data]


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=True)
