# frontend/views/filters.py
from dash import html, dcc


def collapsible_checklist(
    *,
    title: str,
    component_id: str,
    options=None,
    open=False,
    details_id=None,
    summary_id=None,
):
    return html.Details(
        id=details_id,
        open=open,
        style={"width": "100%"},
        children=[
            html.Summary(title, id=summary_id, className="filter_summary"),
            html.Div(
                className="filter_box",
                children=[
                    dcc.Checklist(
                        id=component_id,
                        options=options or [],
                        value=[],
                        inputStyle={"marginRight": "10px"},
                        labelStyle={
                            "display": "flex",
                            "alignItems": "center",
                            "padding": "6px 8px",
                        },
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                            "gap": "2px",
                        },
                    )
                ],
            ),
        ],
    )
