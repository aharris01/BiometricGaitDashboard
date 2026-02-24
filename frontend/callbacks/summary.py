# frontend/callbacks/summary.py
from dash import Input, Output, State, callback
from dash.exceptions import PreventUpdate

from frontend.views.summary_view import SummaryView


def register(app, *, cmap):
    @callback(
        Output("summary-container", "children", allow_duplicate=True),
        Input("summary-show-all", "value"),
        Input("summary-step-slider", "value"),
        State("footsteps-store", "data"),
        prevent_initial_call=True,
    )
    def update_summary(show_all_value, step_index, cached):
        if not cached or not cached.get("event_id"):
            raise PreventUpdate

        show_all = bool(show_all_value and "all" in show_all_value)

        return SummaryView(
            cached["event_id"],
            cmap,
            cached.get("p100", []),
            cached.get("grf", []),
            cached.get("footsteps", []),
            step_p100s=cached.get("footstep_details", []),
            show_all=show_all,
            step_index=int(step_index or 0),
        ).render()
