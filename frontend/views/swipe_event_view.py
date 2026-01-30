# frontend/views/swipe_event_view.py
from dash.dcc import Dropdown
from dash.html import Div, Button

CONTROL_STYLE = {"flex": "1", "minWidth": "160px"}


def SwipeEventView():
    """
    Existing Swipe Events UI moved out of layout.py.
    IMPORTANT: IDs are unchanged so your current callbacks keep working.
    """
    return Div(
        id="swipe-view",
        children=[
            Div(
                id="dropdown-container",
                className="dropdown-container",
                children=[
                    Dropdown(
                        id={"type": "dropdown", "name": "participant", "level": 4},
                        style=CONTROL_STYLE,
                        clearable=True,
                    ),
                    Dropdown(
                        id={"type": "dropdown", "name": "date", "level": 3},
                        style=CONTROL_STYLE,
                        clearable=True,
                    ),
                    Dropdown(
                        id={"type": "dropdown", "name": "direction", "level": 2},
                        style=CONTROL_STYLE,
                        clearable=True,
                    ),
                    Dropdown(
                        id={"type": "dropdown", "name": "event", "level": 1},
                        style=CONTROL_STYLE,
                        clearable=True,
                    ),
                    Button("Submit", id="submit-button"),
                ],
            ),
            Div(id="metrics-graph-container"),
            Div(id="metrics-graph-click-data"),
            Div(id="summary-container"),
        ],
    )
