from dash import Dash, Input, Output, callback
from dash.dcc import Dropdown, Interval
from dash.html import Div
from dash.exceptions import PreventUpdate
import requests

API_BASE = "http://127.0.0.1:8000"

app = Dash(__name__, prevent_initial_callbacks=True)


app.layout = Div(
    id="page",
    children=[
        Interval(id="page-load", max_intervals=1),
        Div(
            id="dropdown-container",
            children=[
                Dropdown(id="participant-dropdown"),
                Dropdown(id="date-dropdown"),
                Dropdown(id="direction-dropdown"),
                Dropdown(id="event-dropdown")
            ],
        ),
    ],
)


@callback(
    Output("participant-dropdown", "options"),
    Input("page-load", "n_intervals"))
def getParticipants(_):
    resp = requests.get(f"{API_BASE}/api/participants", timeout=5)
    resp.raise_for_status()
    data = resp.json()
    return [{"label": str(p), "value": p} for p in data['items']]


@callback(
    Output("date-dropdown", "options"),
    Input("participant-dropdown", "value"))
def getDates(participant):
    if participant is None:
        raise PreventUpdate
    resp = requests.get(f"{API_BASE}/api/participants/{participant}/dates", timeout=5)
    resp.raise_for_status()
    data = resp.json()
    return [{"label": str(date), "value": str(date)} for date in data['items']]

@callback(
    Output("direction-dropdown", "options"),
    Input("participant-dropdown", "value"),
    Input("date-dropdown","value"))
def getDirections(participant, datestr):
    if participant is None or datestr is None: # if no participant callback is not fired
        raise PreventUpdate
    resp = requests.get(f"{API_BASE}/api/participants/{participant}/dates/{datestr}/directions", timeout=5)
    resp.raise_for_status()
    data = resp.json()
    return [{"label": str(direction), "value":direction} for direction in data['items']]

# WORK IN PROGRESS
# @callback(
#     Output("event-dropdown", "options"),
#     Input("participant-dropdown", "value"),
#     Input("date-dropdown","value"),
#     Input("event-dropdown","value"))
# def getEvents(participant, datestr, direction):
#     if participant is None or datestr is None or direction is None:
#         raise PreventUpdate # do not call API if any var is null
#     resp = requests.get(f"{API_BASE}/api/participants/{participant}/dates/{datestr}/directions/{direction}/eventsByDirection", timeout=5)
#     resp.raise_for_status()
#     data = resp.json()
#     return [{"label": str(event), "value":event} for event in data['items']]

def runDash():
    app.run(host="127.0.0.1", port=8050, debug=False)
