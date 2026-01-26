# frontend/views/filters.py
from dash import html, dcc


def ParticipantMultiSelect(*, id: str, options=None, placeholder="Select participants..."):
    return html.Div(
        className="metrics-field",
        children=[
            html.Label("by participant"),
            dcc.Dropdown(
                id=id,
                options=options or [],
                multi=True,
                placeholder=placeholder,
                clearable=True,
            ),
        ],
    )


def DateSelector(*, id: str, placeholder="Select date..."):
    return html.Div(
        className="metrics-field",
        children=[
            html.Label("by date"),
            dcc.DatePickerSingle(
                id=id,
                placeholder=placeholder,
                display_format="YYYY-MM-DD",
                clearable=True,
            ),
        ],
    )
