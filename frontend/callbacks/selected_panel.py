# frontend/callbacks/selected_panel.py

from dash import Input, Output, State, callback, html, dcc, ctx
from dash.exceptions import PreventUpdate
from typing import Any, cast

from frontend.utils import with_select_all


@callback(
    Output("metrics_selected_panel_mode_store", "data"),
    Input("btn-selected-select-mode", "n_clicks"),
    State("metrics_selected_panel_mode_store", "data"),
    prevent_initial_call=True,
)
def toggle_selected_panel_mode(_n, mode_store):
    current = (mode_store or {}).get("mode", "view")
    new_mode = "select" if current == "view" else "view"
    return {"mode": new_mode}


@callback(
    Output("btn-selected-select-mode", "className"),
    Output("btn-selected-select-mode", "children"),
    Input("metrics_selected_panel_mode_store", "data"),
    prevent_initial_call=False,
)
def style_select_toggle_button(mode_store):
    mode = (mode_store or {}).get("mode", "view")

    base = "ok-btn"  # reuse existing style
    active = f"{base} toggle-btn-active" if mode == "select" else base

    return active, "Select"



@callback(
    Output("metrics-selected-list", "children"),
    Input("metrics_selected_events_store", "data"),
    Input("metrics_selected_panel_mode_store", "data"),
    State("metrics_selected_checklist_store", "data"),
    prevent_initial_call=False,
)
def render_selected_list(selected_store, mode_store, checklist_value_store):
    event_ids = (selected_store or {}).get("event_ids", [])
    mode = (mode_store or {}).get("mode", "view")

    if not event_ids:
        return "(selected items here)"

    # VIEW MODE: clickable buttons (your current behavior)
    if mode != "select":
        return html.Div(
            children=[
                html.Div(
                    html.Button(
                        eid,
                        id={"type": "selected_event", "event_id": eid},
                        style={
                            "width": "100%",
                            "textAlign": "left",
                            "padding": "8px 10px",
                            "border": "1px solid #e5e7eb",
                            "borderRadius": "8px",
                            "background": "white",
                            "cursor": "pointer",
                        },
                    ),
                    style={"marginBottom": "8px"},
                )
                for eid in event_ids
            ]
        )

    # SELECT MODE: checklist with Select all at top
    options = with_select_all([{"label": eid, "value": eid} for eid in event_ids])

    # optional: preserve current checklist selection if present
    current_values = (checklist_value_store or {}).get("value", [])

    options = cast(Any, with_select_all(
        [{"label": eid, "value": eid} for eid in event_ids]
    ))

    return html.Div(
        children=[
            dcc.Checklist(
                id="metrics_selected_checklist",
                options=options,
                value=current_values,
                inputStyle={"marginRight": "10px"},
                labelStyle={
                    "display": "flex",
                    "alignItems": "center",
                    "padding": "6px 8px",
                },
                style={"display": "flex", "flexDirection": "column", "gap": "2px"},
            )
        ]
    )
