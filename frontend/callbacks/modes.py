# frontend/callbacks/modes.py
# frontend/callbacks/modes.py
from dash import Input, Output, State, callback, ctx, no_update


def register(app):
    @callback(
        Output("mode-store", "data"),
        Input("btn-mode-swipe", "n_clicks"),
        Input("btn-mode-footstep", "n_clicks"),
        State("mode-store", "data"),
        prevent_initial_call=True,
    )
    def set_mode(_sw, _ft, mode_data):
        triggered = ctx.triggered_id
        current = (mode_data or {}).get("mode", "swipe")

        if triggered == "btn-mode-swipe":
            return {"mode": "swipe", "prev_mode": current}

        if triggered == "btn-mode-footstep":
            return {"mode": "footstep", "prev_mode": current}

        return no_update

    @callback(
        Output("swipe-view", "className"),
        Output("footstep-view", "className"),
        Output("btn-mode-swipe", "className"),
        Output("btn-mode-footstep", "className"),
        Input("mode-store", "data"),
        prevent_initial_call=False,
    )
    def show_hide_views(mode_data):
        mode = (mode_data or {}).get("mode", "swipe")

        swipe_cls = "" if mode == "swipe" else "hidden"
        footstep_cls = "" if mode == "footstep" else "hidden"

        swipe_btn = "mode-btn mode-btn-active" if mode == "swipe" else "mode-btn"
        footstep_btn = "mode-btn mode-btn-active" if mode == "footstep" else "mode-btn"

        return swipe_cls, footstep_cls, swipe_btn, footstep_btn

    @callback(
        Output("header-title", "children"),
        Output("header-subtitle", "children"),
        Input("mode-store", "data"),
        prevent_initial_call=False,
    )
    def update_header(mode_data):
        mode = (mode_data or {}).get("mode", "swipe")

        if mode == "swipe":
            return "Swipe Events", "Footstep extraction QA"

        if mode == "footstep":
            return "Footsteps", "Footstep-level inspection"

        return "Swipe Events", "Footstep extraction QA"
