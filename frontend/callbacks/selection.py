# frontend/callbacks/selection.py
from dash import Input, Output, State, ALL, MATCH, ctx
from dash.exceptions import PreventUpdate

PINK = "rgba(255,0,255,0.9)"
GREEN = "rgba(0,200,0,0.95)"


def register(app, *, cmap):
    @app.callback(
        Output({"type": "p100-graph", "event_id": MATCH}, "figure"),
        Input({"type": "step-thumb", "event_id": MATCH, "step_id": ALL}, "n_clicks"),
        State({"type": "p100-graph", "event_id": MATCH}, "figure"),
        State("footsteps-store", "data"),
        prevent_initial_call=True,
    )
    def click_thumbnail_highlight_bbox(_all_clicks, p100_fig, footsteps_store):
        triggered = ctx.triggered_id
        if not triggered or "step_id" not in triggered or "event_id" not in triggered:
            raise PreventUpdate

        event_id = str(triggered["event_id"])
        step_id = triggered["step_id"]

        if not p100_fig or not footsteps_store:
            raise PreventUpdate

        footsteps_by_event = footsteps_store.get("by_event", {})
        footsteps = footsteps_by_event.get(event_id, [])
        if not footsteps:
            raise PreventUpdate

        # rebuild shapes: selected -> green, others -> pink
        new_shapes = []
        for box in footsteps:
            color = GREEN if str(box.get("id")) == str(step_id) else PINK
            new_shapes.append(
                dict(
                    type="rect",
                    name="bbox",
                    x0=box["x_min"],
                    x1=box["x_max"],
                    y0=box["y_min"],
                    y1=box["y_max"],
                    line=dict(color=color, width=3),
                    fillcolor="rgba(0,0,0,0)",
                )
            )

        fig = p100_fig.copy()
        fig.setdefault("layout", {})
        fig["layout"]["shapes"] = new_shapes

        return fig

    @app.callback(
        Output("selected-step-store", "data"),
        Input({"type": "step-thumb", "event_id": ALL, "step_id": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def store_selected_step(_all_clicks):
        triggered = ctx.triggered_id
        if not triggered or "step_id" not in triggered or "event_id" not in triggered:
            raise PreventUpdate

        return {"event_id": str(triggered["event_id"]), "step_id": triggered["step_id"]}

    @app.callback(
        Output("metrics_selected_events_store", "data", allow_duplicate=True),
        Output("metrics_selected_checklist_store", "data", allow_duplicate=True),
        Input("btn-remove-selected", "n_clicks"),  # your "◀" button
        State("metrics_selected_panel_mode_store", "data"),
        State("metrics_selected_events_store", "data"),
        State("metrics_selected_checklist_store", "data"),
        State("metrics_scatter_selection_store", "data"),
        prevent_initial_call=True,
    )
    def remove_selected_events(
        _n, mode_store, selected_store, checklist_store, scatter_selection_store
    ):
        mode = (mode_store or {}).get("mode", "view")
        existing = (selected_store or {}).get("event_ids", [])
        if not existing:
            raise PreventUpdate

        remove_ids = []
        if mode == "select":
            vals = (checklist_store or {}).get("value", []) or []
            remove_ids = [v for v in vals if v != "__all__"]

        if not remove_ids:
            remove_ids = (scatter_selection_store or {}).get("event_ids", []) or []

        if not remove_ids:
            remove_ids = [existing[-1]]

        remove_set = set(remove_ids)
        new_existing = [eid for eid in existing if eid not in remove_set]

        remaining_checked = []
        if mode == "select":
            prev_checked = (checklist_store or {}).get("value", []) or []
            remaining_checked = [
                v for v in prev_checked if v != "__all__" and v in new_existing
            ]

        return {"event_ids": new_existing}, {"value": remaining_checked}

    @app.callback(
        Output("metrics_filter_participant_open_store", "data"),
        Output("metrics_filter_participant_details", "open"),
        Input("metrics_filter_participant_summary", "n_clicks"),
        State("metrics_filter_participant_open_store", "data"),
        prevent_initial_call=True,
    )
    def toggle_participant_filter_open(_n, open_data):
        # open_data is either True/False (or missing)
        is_open = bool(open_data) if open_data is not None else True
        new_open = not is_open
        return new_open, new_open
