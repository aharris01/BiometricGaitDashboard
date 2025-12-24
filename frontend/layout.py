# frontend/layout.py
from dash.dcc import Dropdown, Interval, Store
from dash.html import Div, Button, H2, Span

CONTROL_STYLE = {"flex": "1", "minWidth": "160px"}


def build_layout():
    return Div(
        id="page",
        className="page",
        children=[
            # ---------- Header ----------
            Div(
                id="header",
                className="header",
                children=[
                    Div(
                        children=[
                            H2("Swipe Summary"),
                            Span(
                                "Footstep extraction QA",
                                className="subtitle",
                            ),
                        ],
                    ),
                    Span(
                        "Local API: 127.0.0.1:8000",
                        className="subtitle",
                    ),
                ],
            ),
            # ---------- Main Content ----------
            Div(
                id="content",
                className="content",
                children=[
                    # hidden sink (unchanged)
                    Div(
                        id={"type": "dropdown-log-sink", "name": "participant", "level": 4},
                        className="hidden",
                    ),
                    # stores
                    Store(
                        id="event-id-store",
                        data={"event_id": None},
                        storage_type="session",
                    ),
                    Store(
                        id="footsteps-store",
                        data=None,
                        storage_type="session",
                    ),
                    # selected step id from thumbnail click
                    Store(
                        id="selected-step-store",
                        data={"step_id": None},
                        storage_type="session",
                    ),
                    # page load trigger
                    Interval(id="page-load", max_intervals=1),
                    # ---------- Dropdown Row ----------
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
                            Button(
                                "Submit",
                                id="submit-button",
                            ),
                        ],
                    ),
                    # ---------- Views ----------
                    Div(id="metrics-graph-container"),
                    Div(id="summary-container"),
                ],
            ),
        ],
    )
