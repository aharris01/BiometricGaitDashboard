# frontend/views/swipe_event_view.py
from dash import dcc
from dash.html import Button, Div

CONTROL_STYLE = {"flex": "1", "minWidth": "160px"}


def SwipeEventView():
    """
    Existing Swipe Events UI moved out of layout.py.
    IMPORTANT: IDs are unchanged so your current callbacks keep working.
    """
    return Div(
        id="swipe-view",
        children=[
            Div(id="metrics-graph-container"),
            Div(id="metrics-graph-click-data"),
            Div(id="summary-container"),
            Div(
                id="summary-pagination-controls",
                style={
                    "display": "none",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "flexDirection": "column",
                    "gap": "8px",
                    "marginTop": "10px",
                    "width": "100%",
                },
                children=[
                    Div(
                        id="summary-pagination-status",
                        style={"fontSize": "13px", "color": "#6b7280"},
                    ),
                    dcc.Loading(
                        id="summary-pagination-loading",
                        type="circle",
                        children=Div(
                            id="summary-pagination-load-wrap",
                            children=[
                                Button(
                                    "Load more",
                                    id="btn-load-more-summaries",
                                    className="ok-btn",
                                    n_clicks=0,
                                ),
                                Div(
                                    id="summary-pagination-loading-sink",
                                    className="hidden",
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        ],
    )
