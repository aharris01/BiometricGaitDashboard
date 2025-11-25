from dash import Dash, Input, Output, State, callback, dcc
from dash.dcc import Dropdown, Interval, Store
from dash.html import Div, Button
from dash.exceptions import PreventUpdate
import requests
import plotly.express as px

from frontend.views import summary_view

API_BASE = "http://127.0.0.1:8000"
CONTROL_STYLE = {"flex": "1", "minWidth": "160px"}

app = Dash(__name__, prevent_initial_callbacks=True)


def fetch_json(url, *, timeout=5, context="API request"):
    """Fetch JSON from the API and log readable errors"""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        message = f"[{context}] Failed to fetch {url}: {exc}"
        app.logger.error(message)
        raise PreventUpdate


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
        Store(id="event-id-store", data={"event_id": None}, storage_type="session"),
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
        Div(
            dcc.Graph(id='p100-graph'),
            style={
                "height": "75vh",
                "maxWidth": "1500px",
                "flex": "1",
                "display": "flex",
                "justifyContent": "center",
            }
        ),
        Div(
            id="swipe-event-visualization",
            children=[summary_view.SummaryView(event_id=None).render()],
        ),
        Div(id="store-data", children=[]),
    ],
)


@callback(Output("participant-dropdown", "options"), Input("page-load", "n_intervals"))
def getParticipants(_):
    data = fetch_json(f"{API_BASE}/api/participants", context="getParticipants")
    return [{"label": str(p), "value": p} for p in data["items"]]


@callback(Output("date-dropdown", "options"), Input("participant-dropdown", "value"))
def getDates(participant):
    require_values(participant)
    data = fetch_json(
        f"{API_BASE}/api/participants/{participant}/dates", context="getDates"
    )
    return [{"label": str(date), "value": str(date)} for date in data["items"]]


@callback(
    Output("direction-dropdown", "options"),
    State("participant-dropdown", "value"),
    Input("date-dropdown", "value"),
)
def getDirections(participant, datestr):
    require_values(participant, datestr)
    data = fetch_json(
        f"{API_BASE}/api/participants/{participant}/dates/{datestr}/directions",
        context="getDirections",
    )
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
    require_values(participant, datestr, direction)
    data = fetch_json(
        f"{API_BASE}/api/participants/{participant}/dates/{datestr}/directions/{direction}/events",
        context="getEvents",
    )
    return [{"label": str(event), "value": event} for event in data["items"]]


@callback(
    Output("swipe-event-metadata", "children"),
    Output("event-id-store", "data"),
    Input("submit-button", "n_clicks"),
    State("participant-dropdown", "value"),
    State("date-dropdown", "value"),
    State("direction-dropdown", "value"),
    State("event-dropdown", "value"),
)
def getSwipeEventId(_, participant, datestr, direction, event):
    require_values(participant, datestr, direction, event)
    data = fetch_json(
        f"{API_BASE}/api/swipe/{participant}/{datestr}/{direction}/{event}",
        context="getSwipeEventId",
    )
    event_id = data["id"]
    return f"Swipe Event ID: {event_id}", {"event_id": event_id}


# Define the color map to be used in the graphs
cmap = px.colors.sequential.Jet
cmap[0] = "#000000"  # Set the 0 value of the color map to black


@app.callback(
    Output("p100-graph", "figure"),
    Input("event-id-store", "data")
)
def display_summary_graph(store_data):
    if store_data is None or store_data.get("event_id") is None:
        raise PreventUpdate
    event_id = store_data["event_id"]
    data = fetch_json(
        f"{API_BASE}/api/events/{event_id}/p100",
        context="display_summary_graph",
    )
    trial = data["p100"]
    fig = px.imshow(trial, color_continuous_scale=cmap)
    return fig


@callback(Output("store-data", "children"), Input("event-id-store", "data"))
def displayStoredData(store_data):
    if store_data is None or store_data.get("event_id") is None:
        raise PreventUpdate
    return f"Stored Event ID: {store_data['event_id']}"


def runDash():
    app.run(host="127.0.0.1", port=8050, debug=False)


def require_values(*args):
    if any(arg is None for arg in args):
        print("Missing parameters; skipping data fetch.")
        raise PreventUpdate
