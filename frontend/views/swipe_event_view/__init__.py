from dash import html

CONTROL_STYLE = {"flex": "1", "minWidth": "160px"}


def SwipeEventView():
    """
    Existing Swipe Events UI moved out of layout.py.
    IMPORTANT: IDs are unchanged so your current callbacks keep working.
    """
    return html.Div(
        id="swipe-view",
        children=[
            html.Div(id="metrics-graph-container"),
            html.Div(id="metrics-graph-click-data"),
            # Always show a visible placeholder so the section is not "missing"
            html.Div(
                id="summary-container",
                children=html.Div(
                    children=[
                        html.H3(
                            "Swipe Event Summary",
                            style={"margin": "0 0 8px 0", "fontSize": "18px"},
                        ),
                        html.Div(
                            "Select an event (click a point in the scatter plot) to load the summary and footsteps.",
                            style={"color": "#6b7280"},
                        ),
                    ],
                    style={
                        "background": "white",
                        "border": "1px solid #e5e7eb",
                        "borderRadius": "8px",
                        "padding": "12px",
                        "boxSizing": "border-box",
                        "minHeight": "200px",
                        "width": "100%",
                    },
                ),
            ),
        ],
    )