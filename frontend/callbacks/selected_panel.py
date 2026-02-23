# frontend/callbacks/selected_panel.py

from typing import Any, cast

from dash import Input, Output, State, callback, html, dcc, ctx, ALL
from dash.exceptions import PreventUpdate

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
    Output("btn-remove-selected", "disabled"),
    Input("metrics_selected_panel_mode_store", "data"),
    prevent_initial_call=False,
)
def disable_remove_button(mode_store):
    mode = (mode_store or {}).get("mode", "view")
    return mode != "select"


@callback(
    Output("btn-selected-confirm", "disabled"),
    Input("metrics_selected_events_store", "data"),
    Input("metrics_selected_panel_mode_store", "data"),
    prevent_initial_call=False,
)
def disable_confirm_button(selected_store, mode_store):
    mode = (mode_store or {}).get("mode", "view")
    if mode == "select":
        # In select mode, allow confirming checklist choices (including empty).
        return False

    event_ids = (selected_store or {}).get("event_ids", [])
    return not bool(event_ids)


@callback(
    Output("metrics_confirmed_events_store", "data"),
    Output("metrics_selected_panel_mode_store", "data", allow_duplicate=True),
    Output("event-id-store", "data", allow_duplicate=True),
    Input("btn-selected-confirm", "n_clicks"),
    State("metrics_selected_events_store", "data"),
    State("metrics_selected_panel_mode_store", "data"),
    State("metrics_selected_checklist_store", "data"),
    prevent_initial_call=True,
)
def confirm_selected_events(_n, selected_store, mode_store, checklist_store):
    event_ids = (selected_store or {}).get("event_ids", [])

    mode = (mode_store or {}).get("mode", "view")
    confirmed = list(event_ids)

    # In select mode, confirm only checked entries.
    if mode == "select":
        checked = [
            v for v in (checklist_store or {}).get("value", []) if v and v != "__all__"
        ]
        if checked:
            checked_set = set(checked)
            confirmed = [eid for eid in event_ids if eid in checked_set]
        else:
            # No checklist marks means "confirm the current draft list as-is".
            confirmed = list(event_ids)

    next_event_store = {"event_id": confirmed[0]} if confirmed else {"event_id": None}
    return {"event_ids": confirmed}, {"mode": "view"}, next_event_store


@callback(
    Output("event-id-store", "data", allow_duplicate=True),
    Input({"type": "selected_event", "event_id": ALL}, "n_clicks"),
    State("metrics_selected_panel_mode_store", "data"),
    State("metrics_confirmed_events_store", "data"),
    prevent_initial_call=True,
)
def pick_event_from_selected_list(_clicks, mode_store, confirmed_store):
    mode = (mode_store or {}).get("mode", "view")

    # Only allow changing summary by clicking items when Select is OFF.
    if mode != "view":
        raise PreventUpdate

    triggered = ctx.triggered_id
    if not triggered or "event_id" not in triggered:
        raise PreventUpdate

    event_id = triggered["event_id"]
    confirmed_ids = set((confirmed_store or {}).get("event_ids", []))
    if event_id not in confirmed_ids:
        raise PreventUpdate

    return {"event_id": event_id}


@callback(
    Output("metrics-selected-list", "children"),
    Input("metrics_selected_events_store", "data"),
    Input("metrics_confirmed_events_store", "data"),
    Input("metrics_selected_panel_mode_store", "data"),
    Input("event-id-store", "data"),
    State("metrics_selected_checklist_store", "data"),
    prevent_initial_call=False,
)
def render_selected_list(
    selected_store,
    confirmed_store,
    mode_store,
    event_store,
    checklist_value_store,
):
    event_ids = (selected_store or {}).get("event_ids", [])
    confirmed_ids = set((confirmed_store or {}).get("event_ids", []))
    mode = (mode_store or {}).get("mode", "view")
    active_event_id = (event_store or {}).get("event_id")

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
                        className="selected-event-btn active"
                        if (eid == active_event_id and eid in confirmed_ids)
                        else "selected-event-btn",
                        disabled=eid not in confirmed_ids,
                        title="Confirmed" if eid in confirmed_ids else "Not confirmed",
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

    return html.Div(
        children=[
            dcc.Checklist(
                id="metrics_selected_checklist",
                options=cast(Any, options),
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
