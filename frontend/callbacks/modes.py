# frontend/callbacks/modes.py
from dash import Input, Output, State, callback, ctx, no_update


def register(app):
    @callback(
        Output("mode-store", "data"),
        Output("pipeline-dialog", "displayed"),
        Input("btn-mode-swipe", "n_clicks"),
        Input("btn-mode-footstep", "n_clicks"),
        Input("btn-mode-pipeline", "n_clicks"),
        State("mode-store", "data"),
        prevent_initial_call=True,
    )
    def set_mode(_sw, _ft, _pl, mode_data):
        triggered = ctx.triggered_id
        current = (mode_data or {}).get("mode", "swipe")

        # Run Pipeline: popup only (no mode switch)
        if triggered == "btn-mode-pipeline":
            return {"mode": current, "prev_mode": current}, True

        if triggered == "btn-mode-swipe":
            return {"mode": "swipe", "prev_mode": current}, False

        if triggered == "btn-mode-footstep":
            return {"mode": "footstep", "prev_mode": current}, False

        return no_update, False

    @callback(
        Output("swipe-view", "className"),
        Output("footstep-view", "className"),
        Output("btn-mode-swipe", "className"),
        Output("btn-mode-footstep", "className"),
        Output("btn-mode-pipeline", "className"),
        Input("mode-store", "data"),
        prevent_initial_call=False,
    )
    def show_hide_views(mode_data):
        mode = (mode_data or {}).get("mode", "swipe")

        swipe_cls = "" if mode == "swipe" else "hidden"
        footstep_cls = "" if mode == "footstep" else "hidden"

        swipe_btn = "mode-btn mode-btn-active" if mode == "swipe" else "mode-btn"
        footstep_btn = "mode-btn mode-btn-active" if mode == "footstep" else "mode-btn"
        pipeline_btn = "mode-btn"  # popup only, never active

        return swipe_cls, footstep_cls, swipe_btn, footstep_btn, pipeline_btn

    # NEW: header title/subtitle change with mode
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

        # pipeline doesn't switch modes right now, but keep fallback anyway
        if mode == "pipeline":
            return "Run Pipeline", "Local preprocessing"

        return "Swipe Events", "Footstep extraction QA"
