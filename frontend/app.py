from dash import Dash, Input, Output, State, callback
from dash.dcc import Dropdown, Interval
from dash.html import Div, Button
from dash.exceptions import PreventUpdate
import requests

API_BASE = "http://127.0.0.1:8000"
CONTROL_STYLE = {"flex": "1", "minWidth": "160px"}

app = Dash(__name__, prevent_initial_callbacks=True)

app.layout = Div(
    id="page",
    style={
        "minHeight": "100vh",
        "display": "flex",
        "flexDirection": "column",
        "alignItems": "center",
        "justifyContent": "flex-start",
        "padding": "16px",
        "boxSizing": "border-box",
        "gap": "24px",
    },
    children=[
        Interval(id="page-load", max_intervals=1),
        Div(
            id="dropdown-container",
            style={
                "height": "15vh",
                "width": "100%",
                "maxWidth": "900px",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "gap": "8px",
            },
            children=[
                Dropdown(id="participant-dropdown", style=CONTROL_STYLE),
                Dropdown(id="date-dropdown", style=CONTROL_STYLE),
                Dropdown(id="direction-dropdown", style=CONTROL_STYLE),
                Dropdown(id="event-dropdown", style=CONTROL_STYLE),
                Button(
                    id="submit-button",
                    n_clicks=0,
                    children="Submit",
                    style={"height": "38px", "padding": "0 24px"},
                ),
            ],
        ),
        Div(
            id="swipe-event-metadata",
            style={
                "width": "100%",
                "maxWidth": "900px",
                "flex": "1",
                "display": "flex",
                "justifyContent": "center",
            },
            children=[],
        ),
    ],
)


@callback(
    Output("participant-dropdown", "options"),
    Input("page-load", "n_intervals")
)
def getParticipants(_):
    resp = requests.get(f"{API_BASE}/api/participants", timeout=5)
    resp.raise_for_status()
    data = resp.json()
    return [{"label": str(p), "value": p} for p in data["items"]]


@callback(
    Output("date-dropdown", "options"),
    Input("participant-dropdown", "value")
)
def getDates(participant):
    if participant is None:
        raise PreventUpdate
    resp = requests.get(f"{API_BASE}/api/participants/{participant}/dates", timeout=5)
    resp.raise_for_status()
    data = resp.json()
    return [{"label": str(date), "value": str(date)} for date in data["items"]]


@callback(
    Output("direction-dropdown", "options"),
    State("participant-dropdown", "value"),
    Input("date-dropdown", "value"),
)
def getDirections(participant, datestr):
    if (participant is None or datestr is None):  # if no participant callback is not fired
        raise PreventUpdate
    resp = requests.get(
        f"{API_BASE}/api/participants/{participant}/dates/{datestr}/directions",
        timeout=5,
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        {"label": str(direction), "value": direction} for direction in data["items"]
    ]


@callback(
    Output("event-dropdown", "options"),
    State("participant-dropdown", "value"),
    State("date-dropdown", "value"),
    Input("direction-dropdown", "value"),
)
def getEvents(participant, datestr, direction):
    if (participant is None or datestr is None or direction is None):
        raise PreventUpdate  # do not call API if any var is null
    resp = requests.get(
        f"{API_BASE}/api/participants/{participant}/dates/{datestr}/directions/{direction}/events",
        timeout=5,
    )
    resp.raise_for_status()
    data = resp.json()
    return [{"label": str(event), "value": event} for event in data["items"]]

@callback(
    Output("swipe-event-metadata","children"),
    Input("submit-button","n_clicks"),
    State("participant-dropdown","value"),
    State("date-dropdown", "value"),
    State("direction-dropdown", "value"),
    State("event-dropdown","value")
)
def getSwipeEventId(self, participant, datestr, direction, event):
    if (participant is None or datestr is None or direction is None or event is None):
        raise PreventUpdate
    resp = requests.get(
        f"{API_BASE}/api/swipe/{participant}/{datestr}/{direction}/{event}",
        timeout=5
    )
    resp.raise_for_status()
    data = resp.json()
    return f''' 
        {data["id"]}
    '''

def runDash():
    app.run(host="127.0.0.1", port=8050, debug=False)
