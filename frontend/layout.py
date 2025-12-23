# frontend/layout.py
from dash.dcc import Dropdown, Interval, Store
from dash.html import Div, Button

CONTROL_STYLE = {"flex": "1", "minWidth": "160px"}

def build_layout():
    return Div(
        id="page",
        style={
            "height": "100vh",
            "overflowY": "auto",
            "display": "flex",
            "flexDirection": "column",
            "alignItems": "center",
            "justifyContent": "flex-start",
            "padding": "16px",
            "boxSizing": "border-box",
            "gap": "4px",
        },
        children=[
            Div(
                id={"type": "dropdown-log-sink", "name": "participant", "level": 4},
                style={"display": "none"},
            ),
            Store(id="event-id-store", data={"event_id": None}, storage_type="session"),
            Store(id="footsteps-store", data=None, storage_type="session"),
            Interval(id="page-load", max_intervals=1),
            Div(
                id="dropdown-container",
                style={
                    "width": "100%",
                    "maxWidth": "900px",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "gap": "8px",
                },
                children=[
                    Dropdown(id={"type": "dropdown", "name": "participant", "level": 4}, style=CONTROL_STYLE, clearable=True),
                    Dropdown(id={"type": "dropdown", "name": "date", "level": 3}, style=CONTROL_STYLE, clearable=True),
                    Dropdown(id={"type": "dropdown", "name": "direction", "level": 2}, style=CONTROL_STYLE, clearable=True),
                    Dropdown(id={"type": "dropdown", "name": "event", "level": 1}, style=CONTROL_STYLE, clearable=True),
                    Button(id="submit-button", n_clicks=0, children="Submit", style={"height": "38px", "padding": "0 24px"}),
                    Div(id="button-pressed"),
                ],
            ),
            Div(id="metrics-graph-container", style={"marginTop": "0"}),
            Div(id="summary-container", style={"marginTop": "0"}),
        ],
    )
