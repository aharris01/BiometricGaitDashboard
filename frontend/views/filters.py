from dash import html, dcc


def collapsible_checklist(*, title: str, component_id: str, options=None, open=False):
    return html.Details(
        open=open,
        style={"width": "100%"},
        children=[
            html.Summary(title, className="filter_summary"),
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
